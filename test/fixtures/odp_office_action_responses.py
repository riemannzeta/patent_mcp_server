"""Trimmed live responses from POST /api/v1/patent/office-action/search.

Captured 2026-10-14 for application 18402543 (two office actions), with
the documentCode and rejectionTypeBag facets the tool always requests.
"""

OFFICE_ACTION_SEARCH_RESPONSE = {'count': 2,
 'facets': {'documentCode': [{'value': 'CTFR', 'count': 1},
                             {'value': 'CTNF', 'count': 1}],
            'rejectionTypeBag': [{'value': '102', 'count': 2},
                                 {'value': '103', 'count': 2},
                                 {'value': 'Other', 'count': 2},
                                 {'value': '112', 'count': 1}]},
 'requestIdentifier': 'b8cc1b30-846c-488c-8efd-d5f802cc4be5',
 'officeActionDataBag': [{'documentCode': 'CTFR',
                          'lastModifiedDateTime': '2026-10-09T18:32:57',
                          'filingDate': '2024-01-02',
                          'rejectionTypeBag': ['102', '103', 'Other'],
                          'submissionDate': '2026-10-09',
                          'groupArtUnitNumber': 1798,
                          'applicationNumberText': '18402543',
                          'inventionTitle': 'HOUSING FOR A SENSOR AND SENSOR',
                          'documentCodeDescriptionText': 'Final Rejections',
                          'officeActionRecordIdentifier': '87f5a4cced36a7ab5ffef6d3f818b5db',
                          'officeActionText': 'DETAILED ACTION\n'
                                              '\n'
                                              'Notice of Pre-AIA  or AIA  Status\n'
                                              'The present application, filed on or '
                                              'after March 16, 2013, is being examined '
                                              'under the first inventor to file '
                                              'provisions of the AIA .\n'
                                              '\n'
                                              'Remarks\n'
                                              'This office action fully acknowledges '
                                              'Applicant’s remarks and amendments '
                                              'submitted on 28 July 2026.\n'
                                              '\n'
                                              'Status of the claims:\n'
                                              'Claims 1, 3-4, and 7-10 are pending.\n'
                                              'Claims 2 and 5-6 are canceled.\n'
                                              'No claims are withdrawn.\n'
                                              'No claims are newly added.\n'
                                              'Claims 1, 3-4, and 8-10 are amended.\n'
                                              '\n'
                                              '\n'
                                              '\n'
                                              '\n'
                                              '\n'
                                              'Claim Rejections',
                          'obsoleteDocumentIdentifier': 'MUZJAZYBX54X145',
                          'publicStatusIndicator': True},
                         {'documentCode': 'CTNF',
                          'lastModifiedDateTime': '2026-10-07T23:30:00',
                          'filingDate': '2024-01-02',
                          'rejectionTypeBag': ['102', '103', '112', 'Other'],
                          'submissionDate': '2026-06-24',
                          'groupArtUnitNumber': 1798,
                          'applicationNumberText': '18402543',
                          'inventionTitle': 'HOUSING FOR A SENSOR AND SENSOR',
                          'documentCodeDescriptionText': 'Non-Final Rejections',
                          'officeActionRecordIdentifier': '6774a80f2a8522ed4d92c7dd6d20e439',
                          'officeActionText': 'DETAILED ACTION\n'
                                              '\n'
                                              'Notice of Pre-AIA  or AIA  Status\n'
                                              'The present application, filed on or '
                                              'after March 16, 2013, is being examined '
                                              'under the first inventor to file '
                                              'provisions of the AIA .\n'
                                              '\n'
                                              'Claim Rejections - 35 USC § 112\n'
                                              'The following is a quotation of 35 '
                                              'U.S.C. 112(b):\n'
                                              '\n'
                                              '(b)  CONCLUSION.—The specification '
                                              'shall conclude with one or more claims '
                                              'particularly pointing out and '
                                              'distinctly claiming the subject matter '
                                              'which the inventor or a joint inventor '
                                              'regards as the invention.\n'
                                              '\n'
                                              '\n'
                                              'The following is',
                          'obsoleteDocumentIdentifier': 'MQQL87V0173X211',
                          'publicStatusIndicator': True}]}

NOT_FOUND_RESPONSE = {'code': '404',
 'message': 'Not Found',
 'detailedMessage': 'No matching records found, refine your search criteria and try '
                    'again',
 'requestIdentifier': 'ac79cdc4-c8e2-4873-a3fe-197ad1ed768f'}

APPLICATION_LOOKUP_RESPONSE = {'count': 1,
 'patentFileWrapperDataBag': [{'applicationNumberText': '12344137'}],
 'requestIdentifier': '3a0dccba-fef0-4a4e-ae31-4999e0ca64c4'}
