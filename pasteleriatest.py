import streamlit as st
from utils import get_supabase_client
from modules.insumos import show_modulo_insumos

# Configuración de página
st.set_page_config(
    page_title="Pastelería ERP",
    page_icon="🧁",
    layout="wide"
)

# Validar conexión
supabase = get_supabase_client()

# Barra Lateral - Navegación
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3081/3081920.png", width=100) # Icono de pastelería
st.sidebar.title("ERP Pastelería")
st.sidebar.markdown("---")

# ⬇️ Cambiamos 'st.sidebar.radio' por 'st.sidebar.selectbox'
opcion_menu = st.sidebar.selectbox(
    "Selecciona un Módulo:",
    [
        "📦 Insumos / Inventario",
        "🧾 Recetario / Escandallos",
        "🎂 Catálogo de Productos",
        "📅 Pedidos y Encargos",
        "📊 Dashboard / Reportes"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Sistema ERP v1.0 | Conectado a Supabase")

# Enrutamiento de pantallas
if opcion_menu == "📦 Insumos / Inventario":
    show_modulo_insumos()

elif opcion_menu == "🧾 Recetario / Escandallos":
    st.header("🧾 Recetario y Escandallos")
    st.info("Módulo en construcción. Próximamente podrás asociar insumos a recetas y calcular el costo exacto de cada preparación.")

elif opcion_menu == "🎂 Catálogo de Productos":
    st.header("🎂 Catálogo de Productos")
    st.info("Módulo en construcción. Aquí definirás los precios de venta de tus tortas y postres.")

elif opcion_menu == "📅 Pedidos y Encargos":
    st.header("📅 Pedidos y Encargos")
    st.info("Módulo en construcción. Calendario para coordinar entregas y anticipos de clientes.")

elif opcion_menu == "📊 Dashboard / Reportes":
    st.header("📊 Dashboard Financiero y de Mermas")
    st.info("Módulo en construcción. Métricas clave de rendimiento del negocio.")
