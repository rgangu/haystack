import pytest
from fastapi.testclient import TestClient

from haystack import Finder
from haystack.retriever.sparse import ElasticsearchRetriever

# TODO: Add integration tests for other APIs


def get_test_client_and_override_dependencies(reader, document_store_with_docs):
    from rest_api.application import app
    from rest_api.controller import search

    search.document_store = document_store_with_docs
    search.retriever = ElasticsearchRetriever(document_store=document_store_with_docs)
    search.FINDERS = {1: Finder(reader=reader, retriever=search.retriever)}

    return TestClient(app)


@pytest.mark.parametrize("document_store_with_docs", ["elasticsearch"], indirect=True)
@pytest.mark.parametrize("reader", ["farm"], indirect=True)
def test_query_api(reader, document_store_with_docs):
    client = get_test_client_and_override_dependencies(reader, document_store_with_docs)

    query = {
        "size": 1,
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": "Where Paul lives?"
                        }
                    }
                ],
                "filter": [
                    {
                        "terms": {
                            "name": "filename2"
                        }
                    }
                ]
            }
        }
    }

    response = client.post(url="/models/1/query?top_k_reader=1", json=query)
    assert 200 == response.status_code
    response_json = response.json()
    assert 1 == response_json['hits']['total']['value']
    assert 1 == len(response_json['hits']['hits'])
    assert response_json['hits']['hits'][0]["_score"] is not None
    assert response_json['hits']['hits'][0]["_source"]["meta"] is not None
    assert response_json['hits']['hits'][0]["_id"] is not None
    assert "New York" == response_json['hits']['hits'][0]["_source"]["answer"]
    assert "My name is Paul and I live in New York" == response_json['hits']['hits'][0]["_source"]["context"]

