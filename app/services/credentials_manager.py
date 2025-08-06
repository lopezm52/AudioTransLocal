"""
Secure credentials management using macOS Keychain
"""

import keyring


class CredentialsManager:
    """Secure credentials management using macOS Keychain"""
    
    SERVICE_NAME = "com.audiotranslocal.app"
    N8N_API_KEY_ACCOUNT = "n8n_api_key"
    
    def get_n8n_api_key(self):
        """Retrieve n8n API key from Keychain"""
        try:
            api_key = keyring.get_password(self.SERVICE_NAME, self.N8N_API_KEY_ACCOUNT)
            return api_key if api_key else ""
        except Exception as e:
            print("Error retrieving API key from Keychain: " + str(e))
            return ""
    
    def set_n8n_api_key(self, api_key):
        """Store n8n API key in Keychain"""
        try:
            if api_key.strip():
                keyring.set_password(self.SERVICE_NAME, self.N8N_API_KEY_ACCOUNT, api_key.strip())
                return True
            else:
                # If empty key, delete from keychain
                self.delete_n8n_api_key()
                return True
        except Exception as e:
            print("Error storing API key in Keychain: " + str(e))
            return False
    
    def delete_n8n_api_key(self):
        """Delete n8n API key from Keychain"""
        try:
            keyring.delete_password(self.SERVICE_NAME, self.N8N_API_KEY_ACCOUNT)
            return True
        except keyring.errors.PasswordDeleteError:
            # Key doesn't exist, which is fine
            return True
        except Exception as e:
            print("Error deleting API key from Keychain: " + str(e))
            return False
