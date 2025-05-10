from supabase import create_client

# ★ここに自分のSupabase情報を入れる
SUPABASE_URL = "https://svexgvaaeeszdtsbggnf.supabase.co"
SUPABASE_KEY = "REDACTED_SUPABASE_KEY"

# Supabaseクライアントを作成
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 接続できてるかテスト（minusテーブルからデータ取得してみる）
def fetch_minus_data():
    data = supabase.table("minus").select("*").execute()
    return data.data

if __name__ == "__main__":
    results = fetch_minus_data()
    print("取得したデータ:", results)
