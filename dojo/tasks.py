from __future__ import absolute_import
from __future__ import unicode_literals

import tempfile
from datetime import datetime, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.http import urlencode
from celery.utils.log import get_task_logger
from celery.decorators import task
from dojo.models import Finding, Test, Engagement
from django.utils import timezone

from docxtpl import DocxTemplate, RichText, Markdown
from StringIO import StringIO
import pdfkit
import sys
from dojo.celery import app
from dojo.reports.widgets import report_widget_factory
from dojo.utils import add_comment, add_epic, add_issue, update_epic, update_issue, \
                        close_epic, get_system_setting, create_notification

logger = get_task_logger(__name__)

@app.task(bind=True)
def add_alerts(self, runinterval):
    now = timezone.now()

    upcoming_engagements = Engagement.objects.filter(target_start__gt=now+timedelta(days=3),target_start__lt=now+timedelta(days=3)+runinterval).order_by('target_start')
    for engagement in upcoming_engagements:
        create_notification(event='upcoming_engagement',
                           title='Upcoming engagement: %s' % engagement.name,
                           engagement=engagement,
                           recipients=[engagement.lead],
                           url=request.build_absolute_uri(reverse('view_engagement', args=(engagement.id,))))

    stale_engagements = Engagement.objects.filter(
        target_start__gt=now-runinterval,
        target_end__lt=now,
        status='In Progress').order_by('-target_end')
    for eng in stale_engagements:
        create_notification(event='stale_engagement', 
                           title='Stale Engagement: %s' % eng.name,
                           description='The engagement "%s" is stale. Target end was %s.' % (eng.name, eng.target_end.strftime("%b. %d, %Y")),
                           url=reverse('view_engagement', args=(eng.id,)),
                           recipients=[eng.lead])


@app.task(bind=True)
def async_docx_report(self,
                     report=None,
                     template="None",
                     filename='report.docx',
                     report_title=None,
                     report_subtitle=None,
                     report_info=None,
                     context={},
                     uri=None):

    def format_fields(tpl):

        context['engagement'].executive_summary = Markdown(context['engagement'].executive_summary)
        context['engagement'].technical_summary = Markdown(context['engagement'].technical_summary)

        for finding in context['findings']:
            if finding.formatting == 'Markdown':
                format_func = Markdown
            else:
                format_func = RichText
            
            finding.pics = [InlineImage(tpl, settings.MEDIA_ROOT+pic.image.name, width=Mm(150)) for pic in finding.images.all()]

            finding.description = format_func(finding.description)
            finding.impact = format_func(finding.impact)
            finding.mitigation = format_func(finding.mitigation)
            finding.references = format_func(finding.references)

    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')

    try:
        report.task_id = async_docx_report.request.id
        report.status = 'running'
        report.save()

        d = DocxTemplate(template)
        format_fields(d)
        d.render(context)

        if report.file.name:
            d.save(report.file.path)
        else:
            rtmp = StringIO()
            d.save(rtmp)
            f = ContentFile(rtmp.getvalue())
            report.file.save(filename, f)

        report.status = 'success'
        report.done_datetime = timezone.now()
        report.save()

        create_notification(event='report_created', 
                            title='Report created',
                            description='The report "%s" is ready.' % report.name,
                            icon='file-text',
                            url=uri, report=report, objowner=report.requester)
    except Exception as e:
        import traceback
        report.status = 'error'
        report.save()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_tb(exc_tb)
        # print(exc_type, exc_tb.tb_lineno)
        raise e

    return True


@app.task(bind=True)
def async_pdf_report(self,
                     report=None,
                     template="None",
                     filename='report.pdf',
                     report_title=None,
                     report_subtitle=None,
                     report_info=None,
                     context={},
                     uri=None):
    xsl_style_sheet = settings.DOJO_ROOT + "/static/dojo/xsl/pdf_toc.xsl"
    x = urlencode({'title': report_title,
                   'subtitle': report_subtitle,
                   'info': report_info})

    cover = context['host'] + reverse(
        'report_cover_page') + "?" + x

    config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH)
    try:
        report.task_id = async_pdf_report.request.id
        report.status = 'running'
        report.save()
        bytes = render_to_string(template, context)
        itoc = context['include_table_of_contents']
        if itoc:
            toc = {'xsl-style-sheet': xsl_style_sheet}
        else:
            toc = None
        pdf = pdfkit.from_string(bytes,
                                 False,
                                 configuration=config,
                                 cover=cover,
                                 toc=toc,
                                 cover_first=True)
        if report.file.name:
            with open(report.file.path, 'w') as f:
                f.write(pdf)
            f.close()
        else:
            f = ContentFile(pdf)
            report.file.save(filename, f)
        report.status = 'success'
        report.done_datetime = timezone.now()
        report.save()

        create_notification(event='report_created', 
                            title='Report created',
                            description='The report "%s" is ready.' % report.name,
                            icon='file-text',
                            url=uri, report=report, objowner=report.requester)
    except Exception as e:
        report.status = 'error'
        report.save()
        # email_requester(report, uri, error=e)
        raise e
    return True


@app.task(bind=True)
def async_custom_pdf_report(self,
                            report=None,
                            template="None",
                            filename='report.pdf',
                            host=None,
                            user=None,
                            uri=None,
                            finding_notes=False,
                            finding_images=False):
    config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH)

    selected_widgets = report_widget_factory(json_data=report.options, request=None, user=user,
                                             finding_notes=finding_notes, finding_images=finding_images, host=host)

    widgets = selected_widgets.values()
    temp = None

    try:
        report.task_id = async_custom_pdf_report.request.id
        report.save()

        toc = None
        toc_depth = 4

        if 'table-of-contents' in selected_widgets:
            xsl_style_sheet_template = "dojo/pdf_toc.xsl"
            temp = tempfile.NamedTemporaryFile()

            toc_settings = selected_widgets['table-of-contents']

            toc_depth = toc_settings.depth
            toc_bytes = render_to_string(xsl_style_sheet_template, {'widgets': widgets,
                                                                    'depth': toc_depth,
                                                                    'title': toc_settings.title})
            temp.write(toc_bytes)
            temp.seek(0)

            toc = {'toc-header-text': toc_settings.title,
                   'xsl-style-sheet': temp.name}

        cover = None
        if 'cover-page' in selected_widgets:
            cp = selected_widgets['cover-page']
            x = urlencode({'title': cp.title,
                           'subtitle': cp.sub_heading,
                           'info': cp.meta_info})
            cover = host + reverse(
                'report_cover_page') + "?" + x
        bytes = render_to_string(template, {'widgets': widgets,
                                            'toc_depth': toc_depth,
                                            'host': host,
                                            'report_name': report.name})
        pdf = pdfkit.from_string(bytes,
                                 False,
                                 configuration=config,
                                 cover=cover,
                                 toc=toc,
                                 )

        if report.file.name:
            with open(report.file.path, 'w') as f:
                f.write(pdf)
            f.close()
        else:
            f = ContentFile(pdf)
            report.file.save(filename, f)
        report.status = 'success'
        report.done_datetime = timezone.now()
        report.save()

        create_notification(event='report_created', title='Report created', description='The report "%s" is ready.' % report.name, url=uri, report=report, objowner=report.requester)
    except Exception as e:
        report.status = 'error'
        report.save()
        # email_requester(report, uri, error=e)
        raise e
    finally:
        if temp is not None:
            # deleting temp xsl file
            temp.close()

    return True

@task(name='add_issue_task')
def add_issue_task( find, push_to_jira):
    logger.info("add issue task")
    add_issue(find, push_to_jira)

@task(name='update_issue_task')
def update_issue_task(find, old_status, push_to_jira):
    logger.info("add issue task")
    update_issue(find, old_status, push_to_jira)

@task(name='add_epic_task')
def add_epic_task(eng, push_to_jira):
    logger.info("add epic task")
    add_epic(eng, push_to_jira)

@task(name='update_epic_task')
def update_epic_task(eng, push_to_jira):
    logger.info("update epic task")
    update_epic(eng, push_to_jira)

@task(name='close_epic_task')
def close_epic_task(eng, push_to_jira):
    logger.info("close epic task")
    close_epic(eng, push_to_jira)

@task(name='add comment')
def add_comment_task(find, note):
    logger.info("add comment")
    add_comment(find, note)

@app.task(name='async_dedupe')
def async_dedupe(new_finding, *args, **kwargs):
    logger.info("running deduplication")
    eng_findings_cwe = Finding.objects.filter(test__engagement__product=new_finding.test.engagement.product,
                                              cwe=new_finding.cwe).exclude(id=new_finding.id).exclude(cwe=None).exclude(endpoints=None)
    eng_findings_title = Finding.objects.filter(test__engagement__product=new_finding.test.engagement.product,
                                                title=new_finding.title).exclude(id=new_finding.id).exclude(endpoints=None)
    total_findings = eng_findings_cwe | eng_findings_title
    for find in total_findings:
        list1 = new_finding.endpoints.all()
        list2 = find.endpoints.all()
        if all(x in list2 for x in list1):
            find.duplicate = True
            super(Finding, find).save(*args, **kwargs)

