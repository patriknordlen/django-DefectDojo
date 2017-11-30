# Description

This fork is a version of Defect Dojo with the aim to better suit consultants. It originally started out with the intent to change the existing code base in such a way that it would be possible to merge back into the main project, however the more I started looking at what I wanted to change the more it became clear that the required changes would need to be made in core parts of DD.

Generally the reason why anyone would use this instead of the main project is that it implements workflows and relational models that better reflect what is relevant to consultants (at least me...) working on assessments that end with a report rather than starting with it.

Main differences compared to the main DD project:

- Models that match a consultant workflow - as one concrete example, instead of product types there are customers
- Uses CVSS for scoring everywhere instead of generic severity levels
- Markdown support for all fields
- Support for generating docx reports
- Decluttered interface with less but more relevant info

Using Markdown in reports is implemented only for docx reports and is in a beta phase. It required my forked version of python-docx-template, available here: https://github.com/patriknordlen/python-docx-template
