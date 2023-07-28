from google.oauth2 import service_account
import ast

class GCPAuth():
    def __init__(self) -> None:
        pass

    @staticmethod
    def get_credentials(gcp_service_account= None):
        '''
        This function returns the credentials for the GCP service account
        '''
        if type(gcp_service_account) == str:
            gcp_service_account = ast.literal_eval(gcp_service_account)

        credentials = service_account.Credentials.from_service_account_info(
            gcp_service_account,
            scopes = [
                "https://www.googleapis.com/auth/cloud-platform",            
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/bigquery",
            ]
        )
 


        return credentials