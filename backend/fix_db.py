import psycopg
from app.core.config import settings

def add_metadata_column():
    conn_str = "postgresql://postgres:postgres@localhost:5434/rural_ai_doctor"
    
    print(f"Connecting to database at localhost:5434...")
    try:
       
        with psycopg.connect(conn_str) as conn:
            
            with conn.cursor() as cur:
                print("Adding 'metadata_json' column to 'medical_documents'...")
                
     
                cur.execute("""
                    ALTER TABLE medical_documents 
                    ADD COLUMN IF NOT EXISTS metadata_json JSONB;
                """)
                conn.commit()
                print("✅ Success! Column 'metadata_json' added.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_metadata_column()