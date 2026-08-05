import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """
    Inicializa y almacena en caché la conexión con Supabase.
    Lee los secrets cargados en Streamlit Cloud o en .streamlit/secrets.toml
    """
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error al leer las credenciales de Supabase: {e}")
        st.stop()
