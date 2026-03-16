# --- 2. 데이터 로드 및 저장 함수 (핵심) ---
SHEET_ID = "1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"

def get_data_via_csv(worksheet_name="Sheet1"):
    try:
        cb = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={worksheet_name}&cb={cb}"
        data = pd.read_csv(url).fillna("")
        
        # 컬럼명 표준화
        data.columns = [str(c).lower().strip() for c in data.columns]
        
        # 데이터가 비어있을 경우 KeyError 방지를 위한 기본 틀 반환
        if data.empty or 'name' not in data.columns:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])
        
        if 'password' in data.columns:
            def clean_pw(val):
                s = str(val).replace("'", "").strip()
                if s.endswith('.0'): s = s[:-2]
                return s
            data['password'] = data['password'].apply(clean_pw)
        return data
    except Exception as e:
        # 에러 발생 시 앱이 중단되지 않도록 빈 구조 반환
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

# [중요] 에러 없는 직접 저장 함수
def save_to_gsheet(dataframe, worksheet_name="Sheet1"):
    try:
        # Secrets에서 [gsheets] 정보를 바로 가져옵니다.
        creds_info = st.secrets["gsheets"]

        # gspread 인증용 데이터 정리
        credentials_dict = {
            "type": creds_info["type"],
            "project_id": creds_info["project_id"],
            "private_key_id": creds_info["private_key_id"],
            "private_key": creds_info["private_key"].replace("\\n", "\n"),
            "client_email": creds_info["client_email"],
            "client_id": creds_info["client_id"],
            "auth_uri": creds_info["auth_uri"],
            "token_uri": creds_info["token_uri"],
            "auth_provider_x509_cert_url": creds_info["auth_provider_x509_cert_url"],
            "client_x509_cert_url": creds_info["client_x509_cert_url"],
        }

        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(worksheet_name)
        
        dataframe = dataframe.fillna("")
        data_to_save = [dataframe.columns.values.tolist()] + dataframe.astype(str).values.tolist()
        
        worksheet.clear()
        worksheet.update(values=data_to_save, range_name='A1')
        return True
    except Exception as e:
        st.error(f"저장 실패! 다시 확인해 주세요: {e}")
        return False
