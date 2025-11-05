"""
Mock responses for Google BigQuery tests.

This module provides sample patent data responses from Google Patents Public Datasets
for use in unit tests without requiring actual BigQuery API calls.
"""

# Sample search results
MOCK_SEARCH_RESULTS = [
    {
        "publication_number": "US-10123456-B2",
        "title_localized": [{"text": "Machine learning system for data analysis", "language": "en"}],
        "abstract_localized": [{"text": "A system for processing data using machine learning algorithms to identify patterns and generate predictions.", "language": "en"}],
        "publication_date": 20200101,
        "filing_date": 20180515,
        "grant_date": 20200101,
        "inventor_harmonized": [
            {"name": "John Smith", "country_code": "US"},
            {"name": "Jane Doe", "country_code": "US"}
        ],
        "assignee_harmonized": [
            {"name": "Tech Corporation", "country_code": "US"}
        ],
        "cpc": [
            {"code": "G06N3/08"},
            {"code": "G06F17/30"}
        ],
        "ipc": [
            {"code": "G06N3/08"}
        ],
        "family_id": "65432100",
        "country_code": "US",
        "application_number": "US-15980123-A"
    },
    {
        "publication_number": "US-10234567-B2",
        "title_localized": [{"text": "Neural network processor with improved efficiency", "language": "en"}],
        "abstract_localized": [{"text": "A specialized processor architecture for executing neural network operations with reduced power consumption.", "language": "en"}],
        "publication_date": 20200115,
        "filing_date": 20180620,
        "grant_date": 20200115,
        "inventor_harmonized": [
            {"name": "Alice Johnson", "country_code": "US"}
        ],
        "assignee_harmonized": [
            {"name": "AI Systems Inc", "country_code": "US"}
        ],
        "cpc": [
            {"code": "G06N3/04"},
            {"code": "G06N3/063"}
        ],
        "ipc": [
            {"code": "G06N3/04"}
        ],
        "family_id": "65432101",
        "country_code": "US",
        "application_number": "US-16012345-A"
    }
]

# Sample patent details
MOCK_PATENT_DETAILS = {
    "publication_number": "US-10123456-B2",
    "title_localized": [{"text": "Machine learning system for data analysis", "language": "en"}],
    "abstract_localized": [{"text": "A system for processing data using machine learning algorithms to identify patterns and generate predictions.", "language": "en"}],
    "publication_date": 20200101,
    "filing_date": 20180515,
    "grant_date": 20200101,
    "priority_date": 20180515,
    "inventor_harmonized": [
        {"name": "John Smith", "country_code": "US", "sequence": 1},
        {"name": "Jane Doe", "country_code": "US", "sequence": 2}
    ],
    "assignee_harmonized": [
        {"name": "Tech Corporation", "country_code": "US", "sequence": 1}
    ],
    "cpc": [
        {"code": "G06N3/08", "first": True},
        {"code": "G06F17/30", "first": False}
    ],
    "ipc": [
        {"code": "G06N3/08", "first": True}
    ],
    "priority_claim": [
        {
            "publication_number": "US-15980123-A",
            "country_code": "US",
            "date": 20180515,
            "kind": "application"
        }
    ],
    "family_id": "65432100",
    "country_code": "US",
    "kind_code": "B2",
    "application_number": "US-15980123-A",
    "pct_number": None,
    "uspc": []
}

# Sample patent claims
MOCK_PATENT_CLAIMS = [
    {
        "claim_num": 1,
        "claim_text": "1. A method for processing data using machine learning, the method comprising: receiving input data from a plurality of sources; preprocessing the input data to generate feature vectors; applying a trained neural network model to the feature vectors; and generating output predictions based on the neural network model outputs."
    },
    {
        "claim_num": 2,
        "claim_text": "2. The method of claim 1, wherein the neural network model comprises multiple layers including at least one convolutional layer and at least one fully connected layer."
    },
    {
        "claim_num": 3,
        "claim_text": "3. The method of claim 2, wherein each layer applies a non-linear activation function selected from the group consisting of ReLU, sigmoid, and tanh."
    },
    {
        "claim_num": 4,
        "claim_text": "4. The method of claim 1, further comprising: collecting training data; and training the neural network model using backpropagation and gradient descent."
    },
    {
        "claim_num": 5,
        "claim_text": "5. A system for data analysis, comprising: a processor; and a memory storing instructions that, when executed by the processor, cause the system to perform the method of claim 1."
    }
]

# Sample patent description
MOCK_PATENT_DESCRIPTION = {
    "publication_number": "US-10123456-B2",
    "description_text": """BACKGROUND

Field of the Invention

The present invention relates generally to machine learning systems, and more particularly to systems and methods for processing data using neural networks.

Description of Related Art

Machine learning has become increasingly important in various applications including image recognition, natural language processing, and predictive analytics. Traditional machine learning approaches often require manual feature engineering and may not scale well to large datasets.

Deep learning using neural networks has emerged as a powerful technique for automatically learning hierarchical representations from data. However, existing neural network systems face challenges in terms of computational efficiency and power consumption.

SUMMARY

The present invention provides a machine learning system that addresses these limitations by implementing an efficient neural network architecture with optimized data processing pipelines.

DETAILED DESCRIPTION

Referring to Figure 1, a machine learning system 100 according to an embodiment of the invention comprises a data input module 110, a preprocessing module 120, a neural network module 130, and an output module 140.

The data input module 110 receives input data from various sources including sensors, databases, and user interfaces. The preprocessing module 120 transforms the input data into feature vectors suitable for neural network processing.

The neural network module 130 implements a deep learning architecture comprising multiple layers. In one embodiment, the architecture includes convolutional layers for feature extraction followed by fully connected layers for classification or regression tasks.

[Additional detailed technical description continues...]""",
    "description_length": 2847
}

# Sample inventor search results
MOCK_INVENTOR_SEARCH_RESULTS = [
    {
        "publication_number": "US-10123456-B2",
        "title_localized": [{"text": "Machine learning system for data analysis", "language": "en"}],
        "publication_date": 20200101,
        "inventor_harmonized": [
            {"name": "John Smith", "country_code": "US"}
        ],
        "assignee_harmonized": [
            {"name": "Tech Corporation", "country_code": "US"}
        ],
        "country_code": "US"
    },
    {
        "publication_number": "US-9876543-B2",
        "title_localized": [{"text": "Data compression method", "language": "en"}],
        "publication_date": 20190315,
        "inventor_harmonized": [
            {"name": "John Smith", "country_code": "US"},
            {"name": "Bob Wilson", "country_code": "US"}
        ],
        "assignee_harmonized": [
            {"name": "Tech Corporation", "country_code": "US"}
        ],
        "country_code": "US"
    }
]

# Sample assignee search results
MOCK_ASSIGNEE_SEARCH_RESULTS = [
    {
        "publication_number": "US-10123456-B2",
        "title_localized": [{"text": "Machine learning system for data analysis", "language": "en"}],
        "publication_date": 20200101,
        "inventor_harmonized": [
            {"name": "John Smith", "country_code": "US"}
        ],
        "assignee_harmonized": [
            {"name": "Google LLC", "country_code": "US"}
        ],
        "country_code": "US"
    },
    {
        "publication_number": "US-10234567-B2",
        "title_localized": [{"text": "Search ranking algorithm", "language": "en"}],
        "publication_date": 20200201,
        "inventor_harmonized": [
            {"name": "Alice Brown", "country_code": "US"}
        ],
        "assignee_harmonized": [
            {"name": "Google LLC", "country_code": "US"}
        ],
        "country_code": "US"
    }
]

# Sample CPC search results
MOCK_CPC_SEARCH_RESULTS = [
    {
        "publication_number": "US-10123456-B2",
        "title_localized": [{"text": "Neural network for image classification", "language": "en"}],
        "publication_date": 20200101,
        "inventor_harmonized": [
            {"name": "John Smith", "country_code": "US"}
        ],
        "assignee_harmonized": [
            {"name": "Tech Corporation", "country_code": "US"}
        ],
        "cpc": [
            {"code": "G06N3/08"}
        ],
        "country_code": "US"
    },
    {
        "publication_number": "US-10345678-B2",
        "title_localized": [{"text": "Deep learning training method", "language": "en"}],
        "publication_date": 20200215,
        "inventor_harmonized": [
            {"name": "Jane Doe", "country_code": "US"}
        ],
        "assignee_harmonized": [
            {"name": "AI Research Inc", "country_code": "US"}
        ],
        "cpc": [
            {"code": "G06N3/08"},
            {"code": "G06N3/04"}
        ],
        "country_code": "US"
    }
]

# Empty results for not found cases
MOCK_EMPTY_RESULTS = []
