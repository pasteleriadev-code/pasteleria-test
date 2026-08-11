import streamlit as st
import pandas as pd
from utils import get_supabase_client

supabase = get_supabase_client()

def show_modulo_recetas():
    st.header("🧾 Recetario y Producción")

    tab_catalogo, tab_nueva, tab_producir = st.tabs([
        "📖 Catálogo de Recetas", 
        "➕ Crear Receta", 
        "👨‍🍳 Registrar Producción"
    ])

    # ---------------------------------------------------------
    # 1. VER RECETAS Y SUS COSTOS
    # ---------------------------------------------------------
    with tab_catalogo:
        st.subheader("Recetas Guardadas")
        try:
            res_recetas = supabase.table("recetas").select("*, receta_detalles(*, insumos(*))").order("nombre").execute()
            recetas = res_recetas.data

            if recetas:
                for r in recetas:
                    costo_total = 0.0
                    detalles_list = []

                    for d in r.get("receta_detalles", []):
                        ins = d.get("insumos")
                        if ins:
                            cant = float(d["cantidad"])
                            costo_u = float(ins["costo_unidad"] or 0)
                            subtotal = cant * costo_u
                            costo_total += subtotal
                            detalles_list.append({
                                "Insumo": ins["nombre"],
                                "Cantidad": cant,
                                "Unidad": ins["unidad_medida"],
                                "Costo Unit. ($)": costo_u,
                                "Subtotal ($)": subtotal
                            })

                    rendimiento = r["rendimiento_porciones"] or 1
                    costo_porcion = costo_total / rendimiento if rendimiento > 0 else 0.0

                    with st.expander(f"🎂 {r['nombre']} — Costo Total: ${costo_total:,.2f} | Rendimiento: {rendimiento} un/porciones"):
                        col_m1, col_m2 = st.columns(2)
                        col_m1.metric("Costo Lote Completo", f"${costo_total:,.2f}")
                        col_m2.metric("Costo por Unid/Porción", f"${costo_porcion:,.2f}")

                        if detalles_list:
                            st.dataframe(
                                pd.DataFrame(detalles_list),
                                column_config={
                                    "Costo Unit. ($)": st.column_config.NumberColumn(format="$%.2f"),
                                    "Subtotal ($)": st.column_config.NumberColumn(format="$%.2f")
                                },
                                use_container_width=True,
                                hide_index=True
                            )

                        if st.button(f"🗑️ Eliminar Receta '{r['nombre']}'", key=f"del_{r['id']}"):
                            supabase.table("recetas").delete().eq("id", r["id"]).execute()
                            st.success("Receta eliminada.")
                            st.rerun()
            else:
                st.info("No hay recetas registradas todavía.")
        except Exception as e:
            st.error(f"Error al cargar recetas: {e}")

    # ---------------------------------------------------------
    # 2. CREAR NUEVA RECETA
    # ---------------------------------------------------------
    with tab_nueva:
        st.subheader("➕ Diseñar Receta")

        res_ins = supabase.table("insumos").select("*").order("nombre").execute()
        insumos = res_ins.data or []

        if not insumos:
            st.warning("⚠️ Debes cargar insumos en el inventario antes de armar recetas.")
            return

        dict_ins = {i["nombre"]: i for i in insumos}

        if "borrador_ingredientes" not in st.session_state:
            st.session_state.borrador_ingredientes = []

        c1, c2, c3 = st.columns([3, 1, 1])
        r_nombre = c1.text_input("Nombre de la Receta *", placeholder="Ej. Torta Pasta Frola")
        r_rendimiento = c2.number_input("Porciones / Rendimiento", min_value=1, value=1)
        r_tiempo = c3.number_input("Tiempo (Mins)", min_value=0, value=45)
        r_desc = st.text_area("Descripción / Preparación", placeholder="Notas del chef...")

        st.markdown("---")
        st.markdown("#### Agregar Insumos a la Receta")
        col_i1, col_i2, col_i3 = st.columns([4, 2, 2])
        ins_sel_nombre = col_i1.selectbox("Seleccionar Insumo", list(dict_ins.keys()))
        ins_obj = dict_ins[ins_sel_nombre]

        cant_ingrediente = col_i2.number_input(f"Cantidad ({ins_obj['unidad_medida']})", min_value=0.01, step=1.0, format="%.2f")
        
        if col_i3.button("➕ Añadir", use_container_width=True):
            costo_u = float(ins_obj["costo_unidad"] or 0)
            st.session_state.borrador_ingredientes.append({
                "insumo_id": ins_obj["id"],
                "nombre": ins_obj["nombre"],
                "cantidad": cant_ingrediente,
                "unidad": ins_obj["unidad_medida"],
                "costo_u": costo_u,
                "subtotal": cant_ingrediente * costo_u
            })
            st.rerun()

        if st.session_state.borrador_ingredientes:
            df_borr = pd.DataFrame(st.session_state.borrador_ingredientes)
            st.dataframe(
                df_borr[["nombre", "cantidad", "unidad", "costo_u", "subtotal"]],
                column_config={
                    "costo_u": st.column_config.NumberColumn("Costo U. ($)", format="$%.2f"),
                    "subtotal": st.column_config.NumberColumn("Subtotal ($)", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

            total_receta = df_borr["subtotal"].sum()
            st.metric("Costo Estimado de Materia Prima", f"${total_receta:,.2f}")

            cb1, cb2 = st.columns(2)
            if cb1.button("❌ Vaciar Borrador", use_container_width=True):
                st.session_state.borrador_ingredientes = []
                st.rerun()

            if cb2.button("💾 Guardar Receta", type="primary", use_container_width=True):
                if not r_nombre.strip():
                    st.error("Ingresa el nombre de la receta.")
                else:
                    try:
                        # Insertar receta
                        rec_res = supabase.table("recetas").insert({
                            "nombre": r_nombre.strip(),
                            "descripcion": r_desc.strip(),
                            "rendimiento_porciones": r_rendimiento,
                            "tiempo_preparacion_min": r_tiempo
                        }).execute()

                        receta_id = rec_res.data[0]["id"]

                        # Insertar detalles
                        for item in st.session_state.borrador_ingredientes:
                            supabase.table("receta_detalles").insert({
                                "receta_id": receta_id,
                                "insumo_id": item["insumo_id"],
                                "cantidad": item["cantidad"]
                            }).execute()

                        st.success(f"¡Receta '{r_nombre}' creada con éxito!")
                        st.session_state.borrador_ingredientes = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    # ---------------------------------------------------------
    # 3. REGISTRAR PRODUCCIÓN
    # ---------------------------------------------------------
    with tab_producir:
        st.subheader("👨‍🍳 Cocinar / Producir Lotes")
        st.caption("Descuenta la materia prima del Inventario y suma el Producto Terminado a la venta.")

        try:
            res_rec = supabase.table("recetas").select("*, receta_detalles(*, insumos(*))").order("nombre").execute()
            recetas_prod = res_rec.data or []

            if recetas_prod:
                dict_r_prod = {r["nombre"]: r for r in recetas_prod}
                r_seleccionada = st.selectbox("Seleccionar Receta a Cocinar", list(dict_r_prod.keys()))
                receta_obj = dict_r_prod[r_seleccionada]

                cp1, cp2 = st.columns(2)
                lotes = cp1.number_input("Cantidad de Tandas / Lotes", min_value=1, value=1)
                porciones_totales = lotes * (receta_obj["rendimiento_porciones"] or 1)
                cp2.metric("Unidades/Porciones a Producir", porciones_totales)

                # Comprobar Stock
                st.markdown("##### 🔍 Chequeo de Stock Requerido")
                detalles = receta_obj.get("receta_detalles", [])
                
                suficiente = True
                items_produccion = []

                for d in detalles:
                    ins = d.get("insumos")
                    if ins:
                        cant_requerida = float(d["cantidad"]) * lotes
                        stock_actual = float(ins["stock_actual"] or 0)
                        ok = stock_actual >= cant_requerida
                        if not ok:
                            suficiente = False

                        items_produccion.append({
                            "insumo_id": ins["id"],
                            "nombre": ins["nombre"],
                            "requerido": cant_requerida,
                            "stock_actual": stock_actual,
                            "unidad": ins["unidad_medida"],
                            "estado": "✅ OK" if ok else "❌ Falta Stock"
                        })

                st.dataframe(
                    pd.DataFrame(items_produccion)[["nombre", "requerido", "stock_actual", "unidad", "estado"]],
                    use_container_width=True,
                    hide_index=True
                )

                if not suficiente:
                    st.error("⚠️ No hay suficiente materia prima para producir esta cantidad de lotes.")

                if st.button("🍳 Confirmar Producción", type="primary", disabled=not suficiente, use_container_width=True):
                    # A) Descontar Insumos
                    for item in items_produccion:
                        nuevo_stock_insumo = item["stock_actual"] - item["requerido"]
                        supabase.table("insumos").update({"stock_actual": nuevo_stock_insumo}).eq("id", item["insumo_id"]).execute()

                    # B) Sumar al Producto Terminado en Productos
                    res_p = supabase.table("productos").select("*").eq("receta_id", receta_obj["id"]).execute()
                    prods_asociados = res_p.data or []

                    if prods_asociados:
                        prod_target = prods_asociados[0]
                        stock_prod_actual = float(prod_target.get("stock_actual") or 0.0)
                        nuevo_stock_prod = stock_prod_actual + porciones_totales
                        
                        supabase.table("productos").update({"stock_actual": nuevo_stock_prod}).eq("id", prod_target["id"]).execute()
                        st.success(f"🎉 ¡Producción exitosa! Se restaron los insumos y se agregaron **+{porciones_totales} unidades** al stock de '{prod_target['nombre']}'.")
                    else:
                        st.warning(f"⚠️ Se descontaron los insumos correctamente, pero la receta **'{receta_obj['nombre']}'** no está vinculada a ningún producto del Catálogo todavía.")

                    st.rerun()
            else:
                st.info("No hay recetas disponibles.")
        except Exception as e:
            st.error(f"Error en la pantalla de producción: {e}")
