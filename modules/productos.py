import streamlit as st
import pandas as pd
from utils import get_supabase_client

supabase = get_supabase_client()

def show_modulo_productos():
    st.header("🎂 Catálogo de Productos")

    tab_catalogo, tab_nuevo, tab_editar = st.tabs([
        "📋 Lista de Productos", 
        "➕ Nuevo Producto", 
        "✏️ Editar Producto"
    ])

    # ---------------------------------------------------------
    # 1. LISTA DE PRODUCTOS
    # ---------------------------------------------------------
    with tab_catalogo:
        st.subheader("Productos Registrados")
        try:
            res = supabase.table("productos").select("*, recetas(*, receta_detalles(*, insumos(*)))").order("nombre").execute()
            productos = res.data or []

            if productos:
                datos = []
                for p in productos:
                    rec = p.get("recetas")
                    costo_materia_prima = 0.0

                    if rec:
                        for d in rec.get("receta_detalles", []):
                            ins = d.get("insumos")
                            if ins:
                                costo_materia_prima += float(d["cantidad"]) * float(ins["costo_unidad"] or 0)

                    precio = float(p["precio_venta"] or 0)
                    ganancia = precio - costo_materia_prima
                    margen = (ganancia / precio * 100) if precio > 0 else 0.0

                    datos.append({
                        "nombre": p["nombre"],
                        "categoria": p.get("categoria") or "Sin cat.",
                        "stock_actual": float(p.get("stock_actual") or 0.0),
                        "precio_venta": precio,
                        "costo_fab": costo_materia_prima if rec else None,
                        "margen": margen if rec else None,
                        "receta": rec["nombre"] if rec else "Sin Receta Directa",
                        "activo": "✅ Sí" if p.get("activo", True) else "❌ No"
                    })

                df = pd.DataFrame(datos)
                st.dataframe(
                    df,
                    column_config={
                        "nombre": "Producto",
                        "categoria": "Categoría",
                        "stock_actual": st.column_config.NumberColumn("Stock Terminado", format="%.2f"),
                        "precio_venta": st.column_config.NumberColumn("Precio Venta ($)", format="$%.2f"),
                        "costo_fab": st.column_config.NumberColumn("Costo Mat. Prima ($)", format="$%.2f"),
                        "margen": st.column_config.NumberColumn("Margen (%)", format="%.1f%%"),
                        "receta": "Receta Asociada",
                        "activo": "Activo"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay productos cargados en el catálogo.")
        except Exception as e:
            st.error(f"Error al listar productos: {e}")

    # ---------------------------------------------------------
    # 2. CREAR PRODUCTO
    # ---------------------------------------------------------
    with tab_nuevo:
        st.subheader("➕ Agregar Producto")

        res_r = supabase.table("recetas").select("*").order("nombre").execute()
        recetas = res_r.data or []
        
        dict_recetas = {"Ninguna (Producto sin Receta)": None}
        for r in recetas:
            dict_recetas[r["nombre"]] = r["id"]

        with st.form("form_nuevo_p", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre del Producto *", placeholder="Ej. Torta Pasta Frola Entera")
            categoria = col2.selectbox("Categoría *", ["Tortas", "Tartas y Pie", "Porciones", "Cupcakes", "Galletas", "Bebidas", "Otros"])

            receta_sel_nombre = st.selectbox("Vincular a Receta", list(dict_recetas.keys()))
            receta_id_sel = dict_recetas[receta_sel_nombre]

            col3, col4, col5 = st.columns(3)
            precio_venta = col3.number_input("Precio de Venta ($) *", min_value=0.0, step=50.0, format="%.2f")
            stock_inicial = col4.number_input("Stock Inicial Listo", min_value=0.0, step=1.0, format="%.2f")
            activo = col5.checkbox("Activo para Venta", value=True)

            if st.form_submit_button("Guardar Producto", use_container_width=True):
                if not nombre.strip():
                    st.error("El nombre del producto es obligatorio.")
                elif precio_venta <= 0:
                    st.error("El precio debe ser mayor a $0.")
                else:
                    try:
                        supabase.table("productos").insert({
                            "nombre": nombre.strip(),
                            "categoria": categoria,
                            "receta_id": receta_id_sel,
                            "precio_venta": precio_venta,
                            "stock_actual": stock_inicial,
                            "activo": activo
                        }).execute()
                        st.success(f"¡Producto '{nombre}' creado con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear producto: {e}")

    # ---------------------------------------------------------
    # 3. EDITAR PRODUCTO
    # ---------------------------------------------------------
    with tab_editar:
        st.subheader("✏️ Modificar o Ajustar Stock / Precios")
        try:
            res_p = supabase.table("productos").select("*").order("nombre").execute()
            prods = res_p.data or []

            if prods:
                dict_p = {f"{p['nombre']} (${p['precio_venta']:,.2f})": p for p in prods}
                p_sel_key = st.selectbox("Seleccionar Producto", list(dict_p.keys()))
                prod_obj = dict_p[p_sel_key]

                with st.form("form_edit_p"):
                    c_e1, c_e2 = st.columns(2)
                    edit_nombre = c_e1.text_input("Nombre", value=prod_obj["nombre"])
                    
                    cats = ["Tortas", "Tartas y Pie", "Porciones", "Cupcakes", "Galletas", "Bebidas", "Otros"]
                    idx_cat = cats.index(prod_obj["categoria"]) if prod_obj.get("categoria") in cats else 0
                    edit_cat = c_e2.selectbox("Categoría", cats, index=idx_cat)

                    c_e3, c_e4, c_e5 = st.columns(3)
                    edit_precio = c_e3.number_input("Precio ($)", value=float(prod_obj["precio_venta"]), step=50.0, format="%.2f")
                    edit_stock = c_e4.number_input("Stock Actual", value=float(prod_obj.get("stock_actual") or 0.0), step=1.0, format="%.2f")
                    edit_activo = c_e5.checkbox("Activo", value=prod_obj.get("activo", True))

                    b_col1, b_col2 = st.columns(2)
                    if b_col1.form_submit_button("💾 Actualizar", use_container_width=True):
                        supabase.table("productos").update({
                            "nombre": edit_nombre,
                            "categoria": edit_cat,
                            "precio_venta": edit_precio,
                            "stock_actual": edit_stock,
                            "activo": edit_activo
                        }).eq("id", prod_obj["id"]).execute()
                        st.success("¡Producto actualizado!")
                        st.rerun()

                    if b_col2.form_submit_button("🗑️ Eliminar", type="secondary", use_container_width=True):
                        supabase.table("productos").delete().eq("id", prod_obj["id"]).execute()
                        st.success("Producto eliminado.")
                        st.rerun()
            else:
                st.info("No hay productos para editar.")
        except Exception as e:
            st.error(f"Error: {e}")
