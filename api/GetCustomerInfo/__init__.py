import logging
import json
import azure.functions as func


def main(req: func.HttpRequest, customerInfo: func.DocumentList) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    customerJson = {}
    if customerInfo:
        logging.info("Found customerInfo item, firstName=%s",
                     customerInfo[0]["firstName"])
        customerJson = {
            "id": customerInfo[0]["id"],
            "fullName": customerInfo[0]["firstName"] + " " + customerInfo[0]["lastName"],
            "orders": customerInfo[0]["orders"]
        }
        
        return func.HttpResponse(
            json.dumps(customerJson),
            status_code=200
        )
    else:
        logging.warning("customerInfo item not found")
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass an id in the query string or in the request body for a personalized response.",
             status_code=200
        )
