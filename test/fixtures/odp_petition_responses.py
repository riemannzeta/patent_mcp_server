"""Trimmed live response from POST /api/v1/petition/decisions/search.

Captured 2026-10-14 for petition type 533 with the query
ocrSearchText:"unintentional delay", so ocrSearchText carries ODP's
HTML highlights. allSearchableFields and the download options are cut short.
"""

PETITION_SEARCH_RESPONSE = {'count': 2817,
 'facets': {'finalDecidingOfficeName': [{'value': 'OFFICE OF PETITIONS',
                                         'count': 2817}],
            'decisionPetitionTypeCode': [{'value': '533', 'count': 2817}],
            'decidedPetitionTypeCodeDescriptionText': [{'value': 'DISMISSED',
                                                        'count': 1713},
                                                       {'value': 'GRANTED',
                                                        'count': 1103},
                                                       {'value': 'DENIED',
                                                        'count': 1}]},
 'requestIdentifier': '2394a22d-07d1-4591-930d-6d91c02e0c46',
 'petitionDecisionDataBag': [{'firstInventorToFileIndicator': False,
                              'petitionMailDate': '2025-09-16',
                              'lastModifiedDateTime': '2026-10-14T07:20:08',
                              'decisionPetitionTypeCode': '533',
                              'applicationNumberText': '12344137',
                              'decidedPetitionTypeCode': 'D',
                              'technologyCenter': '2600',
                              'decidedPetitionTypeCodeDescriptionText': 'DISMISSED',
                              'applicationStatusDate': '2025-07-14',
                              'decisionMailDate': '2026-10-05',
                              'finalPetitionDecisionIndicator': False,
                              'documentBag': [{'documentCode': 'PETDEC',
                                               'documentIdentifier': 'MUWPOE8HX247X37',
                                               'downloadOptionBag': [{'mimeTypeIdentifier': 'PDF',
                                                                      'downloadUrl': 'https://api.uspto.gov/api/v1/download/applications/12344137/MUWPOE8HX247X37.pdf',
                                                                      'pageTotalQuantity': 4},
                                                                     {'mimeTypeIdentifier': 'MS_WORD',
                                                                      'downloadUrl': 'https://api.uspto.gov/api/v1/download/applications/12344137/MUWPOE8HX247X37/files/O.P.%20Petition%20Decision.docx'}],
                                               'officialDate': '2026-10-07T04:00:00',
                                               'documentCodeDescriptionText': 'Petition '
                                                                              'Decision'}],
                              'ocrSearchText': 'The rules and statutory provisions '
                                               'governing the operations of the United '
                                               'States Patent and Trademark Office '
                                               'require payment of a fee on filing '
                                               'each petition to revive an abandoned '
                                               'application for patent based on '
                                               "<b><span style='background-color: "
                                               "yellow;'>unintentional</span></b> "
                                               "<b><span style='background-color: "
                                               "yellow;'>delay</span></b> or to accept "
                                               'an unintentionally delayed payment of '
                                               'a fee for issuing a patent. In this '
                                               'instance, the fee required by law is '
                                               '$904 as a small entity status.  ...',
                              'petitionDecisionRecordIdentifier': '764ea781-7319-5ad7-a9b9-4e115544556e',
                              'finalDecidingOfficeName': 'OFFICE OF PETITIONS',
                              'inventorBag': ['Mark A. Uhlig'],
                              'applicationStatusDescriptionText': 'Patent Expired Due '
                                                                  'to NonPayment of '
                                                                  'Maintenance Fees '
                                                                  'Under 37 CFR 1.362',
                              'businessEntityStatusCategory': 'Small',
                              'patentNumber': '8462371',
                              'customerNumber': 158065,
                              'groupArtUnitNumber': '2673',
                              'inventionTitle': 'SPECIFYING, PRODUCING, AND DELIVERING '
                                                'VARIABLE-CONTENT DOCUMENTS',
                              'decisionDate': '2026-10-05',
                              'decisionPetitionTypeCodeDescriptionText': 'REINSTATE '
                                                                         'PATENT - '
                                                                         'UNINTENTIONALLY '
                                                                         'DELAYED '
                                                                         'PAYMENT OF '
                                                                         'MAINTENANCE '
                                                                         'FEE, NO '
                                                                         'ADDITIONAL '
                                                                         'INFORMATION '
                                                                         'REQUIRED (37 '
                                                                         'CFR '
                                                                         '1.378(A))',
                              'courtActionIndicator': False,
                              'allSearchableFields': '12344137 Patent Expired Due to '
                                                     'NonPayment of Maintenance Fees '
                                                     'Under 37 CFR 1.362 REINSTATE '
                                                     'PATENT - UNINTENTIONALLY DELAYED '
                                                     'PAYMENT OF MAINTENANCE FEE, NO '
                                                     'ADDITIONAL INFORMATION REQUIRED '
                                                     '(37 CFR 1.378(A)) DISMISSED '
                                                     'OFFICE OF PETITIONS SPECIFYING, '
                                                     'PRODUCING, AND DELIVERING '
                                                     'VARIABLE-CONTENT DOCUMENTS Mark '
                                                     'A. Uhlig 8462371 United States '
                                                     'Patent and Trademark Office    \n'
                                                     '        \n'
                                                     '            \n'
                                                     '                                \n'
                                                     '            \n'
                                                     '        \n'
                                                     '    \n'
                                                     '\n'
                                                     'Commissioner for Patents\n'
                                                     'United States Patent and '
                                                     'Trademark Office\n'
                                                     'P.O. Box 1450\n'
                                                     'Alexandria, VA 22313-1450\n'
                                                     'www.uspto.gov\n'
                                                     '\n'
                                                     '\n'
                                                     '\n'
                                                     '\n'
                                                     'In re Patent No. 8,462,3'}]}
