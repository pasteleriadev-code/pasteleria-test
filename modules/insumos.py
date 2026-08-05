import streamlit as st
import pandas as pd
from utils import get_supabase_client

supabase = get_supabase_client()

def show_modulo_insumos():
    st.header("📦 Gestión de Insumos y Materias Primas")

    # Tabs para organizar las acciones
    tab_listado, tab_nuevo = st.tabs(["📋 Inventario Actual", "➕ Registrar Nuevo Insumo"])

    # TAB 1: LISTADO DE INSUMOS
    with tab_listado:
        try:
            res = supabase.table("insumos").select("*").order("nombre").execute()
            data = res.data

            if data:
                df = pd.DataFrame(data)

                # Mostrar métricas de alerta
                insumos_bajo_stock = df[df["stock_actual"] <= df["stock_minimo"]]
                
                col1, col2 = st.columns(2)
                col1.metric("Total de Insumos Registrados", len(df))
                col2.metric("Insumos en Alerta de Stock", len(insumos_bajo_stock), delta_color="inverse")

                if not insumos_bajo_stock.empty:
                    st.warning("⚠️ Hay materias primas por debajo del stock mínimo:")
                    st.dataframe(insumos_bajo_stock[["nombre", "stock_actual", "stock_minimo", "unidad_medida"]], use_container_width=True)

                st.subheader("Listado General")
                st.dataframe(
                    df[["nombre", "unidad_medida", "stock_actual", "stock_minimo", "costo_unidad"]],
                    column_config={
                        "nombre": "Nombre del Insumo",
                        "unidad_medida": "Unidad",
                        "stock_actual": st.column_config.NumberColumn("Stock Actual", format="%.2f"),
                        "stock_minimo": st.column_config.NumberColumn("Stock Mínimo", format="%.2f"),
                        "costo_unidad": st.column_config.NumberColumn("Costo / Unidad ($)", format="$%.4f"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay insumos registrados aún. Agrega el primero en la siguiente pestaña.")
        except Exception as e:
            st.error(f"Error al cargar insumos: {e}")

    # TAB 2: CREAR INSUMO
    with tab_nuevo:
        with st.form("form_nuevo_insumo", clear_on_submit=True):
            st.subheader("Datos de la Materia Prima")
            
            col_a, col_b = st.columns(2)
            nombre = col_a.text_input("Nombre del Insumo *", placeholder="Ej. Harina 0000")
            unidad = col_b.selectbox("Unidad de Medida *", ["gramos", "mililitros", "unidades", "kilos", "litros"])

            col_c, col_d, col_e = st.columns(3)
            stock_actual = col_c.number_input("Stock Inicial", min_value=0.0, step=100.0, format="%.2f")
            stock_minimo = col_d.number_input("Stock Mínimo Alerta", min_value=0.0, step=100.0, format="%.2f")
            costo_unidad = col_e.number_input("Costo por Unidad ($)", min_value=0.0, step=0.001, format="%.4f")

            submitted = st.form_submit_button("Guardar Insumo", use_container_width=True)

            if submitted:
                if not nombre.strip():
                    st.error("El nombre del insumo es obligatorio.")
                else:
                    nuevo_insumo = {
                        "nombre": nombre.strip(),
                        "unidad_medida": unidad,
                        "stock_actual": stock_actual,
                        "stock_minimo": stock_minimo,
                        "costo_unidad": costo_unidad
                    }
                    try:
                        supabase.table("insumos").insert(nuevo_insumo).execute()
                        st.success(f"¡Insumo '{nombre}' registrado con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar en Supabase: {e}")
