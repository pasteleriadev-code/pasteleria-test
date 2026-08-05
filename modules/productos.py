import streamlit as st
import pandas as pd
from utils import get_supabase_client

supabase = get_supabase_client()

def show_modulo_productos():
    st.header("🎂 Catálogo de Productos")

    tab_catalogo, tab_nuevo, tab_editar = st.tabs([
        "📋 Productos Registrados", 
        "➕ Nuevo Producto", 
        "✏️ Modificar Precios y Productos"
    ])

    # ---------------------------------------------------------
    # 1. LISTADO DE PRODUCTOS
    # ---------------------------------------------------------
    with tab_catalogo:
        st.subheader("Menú de Productos a la Venta")
        try:
            # Traer productos con su receta asociada (si tiene)
            res = supabase.table("productos").select("*, recetas(*, receta_detalles(*, insumos(*)))").order("nombre").execute()
            productos = res.data

            if productos:
                listado_prod = []

                for p in productos:
                    rec = p.get("recetas")
                    costo_prod = 0.0

                    # Si está vinculado a una receta, calcular su costo actual de materia prima
                    if rec:
                        for d in rec.get("receta_detalles", []):
                            ins = d.get("insumos")
                            if ins:
                                cant = float(d["cantidad"])
                                c_unit = float(ins["costo_unidad"])
                                costo_prod += (cant * c_unit)

                    precio_venta = float(p["precio_venta"])
                    ganancia = precio_venta - costo_prod
                    margen_porcentaje = (ganancia / precio_venta * 100) if precio_venta > 0 else 0.0

                    listado_prod.append({
                        "id": p["id"],
                        "nombre": p["nombre"],
                        "categoria": p.get("categoria") or "Sin categoría",
                        "precio_venta": precio_venta,
                        "costo_fab": costo_prod if rec else None,
                        "margen": margen_porcentaje if rec else None,
                        "receta": rec["nombre"] if rec else "Venta directa (Sin receta)",
                        "activo": "✅ Sí" if p.get("activo", True) else "❌ No"
                    })

                df = pd.DataFrame(listado_prod)

                # Métricas rápidas
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Productos", len(df))
                c2.metric("Productos Activos", len(df[df["activo"] == "✅ Sí"]))
                c3.metric("Categorías", df["categoria"].nunique())

                st.dataframe(
                    df[["nombre", "categoria", "precio_venta", "costo_fab", "margen", "receta", "activo"]],
                    column_config={
                        "nombre": "Producto",
                        "categoria": "Categoría",
                        "precio_venta": st.column_config.NumberColumn("Precio Venta ($)", format="$%.2f"),
                        "costo_fab": st.column_config.NumberColumn("Costo Mat. Prima ($)", format="$%.2f"),
                        "margen": st.column_config.NumberColumn("Margen (%)", format="%.1f%%"),
                        "receta": "Origen / Receta",
                        "activo": "Activo"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay productos registrados en el catálogo.")
        except Exception as e:
            st.error(f"Error al cargar productos: {e}")

    # ---------------------------------------------------------
    # 2. NUEVO PRODUCTO
    # ---------------------------------------------------------
    with tab_nuevo:
        st.subheader("➕ Agregar Producto al Catálogo")
        
        # Traer recetas disponibles para vincular
        res_r = supabase.table("recetas").select("*, receta_detalles(*, insumos(*))").order("nombre").execute()
        recetas = res_r.data or []
        
        dict_recetas = {"Ninguna (Venta directa / Reventa)": None}
        dict_costos_receta = {}

        for r in recetas:
            costo_r = 0.0
            for d in r.get("receta_detalles", []):
                ins = d.get("insumos")
                if ins:
                    costo_r += float(d["cantidad"]) * float(ins["costo_unidad"])
            
            dict_recetas[f"{r['nombre']} (Costo Mat. Prima: ${costo_r:,.2f})"] = r["id"]
            dict_costos_receta[r["id"]] = costo_r

        with st.form("form_nuevo_producto", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            nombre = col_a.text_input("Nombre del Producto *", placeholder="Ej. Torta Red Velvet Entera")
            categoria = col_b.selectbox("Categoría *", ["Tortas", "Tartas y Pie", "Porciones", "Cupcakes", "Galletas", "Bebidas", "Otros"])

            receta_sel = st.selectbox("Vincular a una Receta (Opcional)", list(dict_recetas.keys()))
            receta_id_sel = dict_recetas[receta_sel]
            costo_referencia = dict_costos_receta.get(receta_id_sel, 0.0)

            if receta_id_sel:
                st.info(f"💡 El costo estimado de materia prima para esta receta es de **${costo_referencia:,.2f}**")

            col_c, col_d = st.columns(2)
            precio_venta = col_c.number_input("Precio de Venta al Público ($) *", min_value=0.0, step=50.0, format="%.2f")
            activo = col_d.checkbox("Producto Activo para Venta", value=True)

            # Cálculo en vivo de ganancia
            if receta_id_sel and precio_venta > 0:
                ganancia_est = precio_venta - costo_referencia
                margen_est = (ganancia_est / precio_venta) * 100
                st.caption(f"📈 Ganancia bruta estimada: **${ganancia_est:,.2f}** ({margen_est:.1f}% de margen)")

            submitted = st.form_submit_button("Guardar Producto", use_container_width=True)

            if submitted:
                if not nombre.strip():
                    st.error("El nombre del producto es obligatorio.")
                elif precio_venta <= 0:
                    st.error("El precio de venta debe ser mayor a $0.")
                else:
                    payload = {
                        "nombre": nombre.strip(),
                        "categoria": categoria,
                        "receta_id": receta_id_sel,
                        "precio_venta": precio_venta,
                        "activo": activo
                    }
                    try:
                        supabase.table("productos").insert(payload).execute()
                        st.success(f"¡Producto '{nombre}' agregado correctamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar producto: {e}")

    # ---------------------------------------------------------
    # 3. MODIFICAR PRODUCTO EXISTENTE
    # ---------------------------------------------------------
    with tab_editar:
        st.subheader("✏️ Editar Producto o Ajustar Precio")
        try:
            res_p = supabase.table("productos").select("*").order("nombre").execute()
            prods = res_p.data

            if prods:
                dict_prods = {f"{p['nombre']} (${p['precio_venta']:,.2f})": p for p in prods}
                prod_sel_key = st.selectbox("Seleccionar Producto:", list(dict_prods.keys()))
                prod_obj = dict_prods[prod_sel_key]

                with st.form("form_edit_producto"):
                    col1, col2 = st.columns(2)
                    edit_nombre = col1.text_input("Nombre", value=prod_obj["nombre"])
                    
                    cats = ["Tortas", "Tartas y Pie", "Porciones", "Cupcakes", "Galletas", "Bebidas", "Otros"]
                    idx_cat = cats.index(prod_obj["categoria"]) if prod_obj.get("categoria") in cats else 0
                    edit_cat = col2.selectbox("Categoría", cats, index=idx_cat)

                    col3, col4 = st.columns(2)
                    edit_precio = col3.number_input("Precio de Venta ($)", value=float(prod_obj["precio_venta"]), step=50.0, format="%.2f")
                    edit_activo = col4.checkbox("Producto Activo", value=prod_obj.get("activo", True))

                    c_b1, c_b2 = st.columns(2)
                    if c_b1.form_submit_button("💾 Actualizar Producto", use_container_width=True):
                        update_payload = {
                            "nombre": edit_nombre,
                            "categoria": edit_cat,
                            "precio_venta": edit_precio,
                            "activo": edit_activo
                        }
                        supabase.table("productos").update(update_payload).eq("id", prod_obj["id"]).execute()
                        st.success("¡Producto actualizado correctamente!")
                        st.rerun()

                    # Opción para eliminar
                    if c_b2.form_submit_button("🗑️ Eliminar Producto", type="secondary", use_container_width=True):
                        supabase.table("productos").delete().eq("id", prod_obj["id"]).execute()
                        st.success("Producto eliminado.")
                        st.rerun()
            else:
                st.info("No hay productos disponibles para editar.")
        except Exception as e:
            st.error(f"Error: {e}")
