$env:CURL_CA_BUNDLE=''
$env:REQUESTS_CA_BUNDLE=''
$env:SSL_CERT_FILE=''

pip install -r frontend_app/requirements.txt
streamlit run frontend_app/app.py
