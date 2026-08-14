import math
import streamlit as st
import pandas as pd
from utils import get_supabase_client

supabase = get_supabase_client()

NOMBRE_RUBRO_PACKAGING = "Empaque y Descartables"


# ---------------------------------------------------------
# FUNCIÓN AUXILIAR DE CÁLCULO DE PRECIO
# ---------------------------------------------------------
def calcular_precio_sugerido(costo_receta: float) -> float:
    """
    Calcula el precio de venta sugerido aplicando:
    1. Margen del 100% sobre el costo (Costo * 2).
    2. Redondeo hacia arriba al siguiente múltiplo de 100.
    """
    if costo_receta <= 0:
        return 0.0

    precio_base = costo_receta * 2.0
    precio_redondeado = math.ceil(precio_base / 100.0) * 100
    return float(precio_redondeado)


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
            res_recetas = (
                supabase.table("recetas")
                .select("*, receta_detalles(*, insumos(*))")
                .order("nombre")
                .execute()
            )
            recetas = res_recetas.data

            if recetas:
                for r in recetas:
                    costo_ingredientes = 0.0
                    costo_packaging = 0.0
                    detalles_list = []

                    for d in r.get("receta_detalles", []):
                        ins = d.get("insumos")
                        if ins:
                            cant = float(d["cantidad"])
                            costo_u = float(ins["costo_unidad"] or 0)
                            subtotal = cant * costo_u
                            rubro_ins = ins.get("rubro", "")

                            is_pkg = rubro_ins == NOMBRE_RUBRO_PACKAGING
                            if is_pkg:
                                costo_packaging += subtotal
                            else:
                                costo_ingredientes += subtotal

                            detalles_list.append({
                                "Tipo": "📦 Packaging" if is_pkg else "🥣 Ingrediente",
                                "Insumo": ins["nombre"],
                                "Rubro": rubro_ins or "Sin Rubro",
                                "Cantidad": cant,
                                "Unidad": ins["unidad_medida"],
                                "Costo Unit. ($)": costo_u,
                                "Subtotal ($)": subtotal
                            })

                    costo_total = costo_ingredientes + costo_packaging
                    rendimiento = r["rendimiento_porciones"] or 1
                    costo_porcion = costo_total / rendimiento if rendimiento > 0 else 0.0

                    with st.expander(
                        f"🎂 {r['nombre']} — Costo Total: ${costo_total:,.2f} | Rendimiento: {rendimiento} porciones"
                    ):
                        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                        c_m1.metric("Ingredientes Comestibles", f"${costo_ingredientes:,.2f}")
                        c_m2.metric("Packaging / Empaque", f"${costo_packaging:,.2f}")
                        c_m3.metric("Costo Total Lote", f"${costo_total:,.2f}")
                        
                        precio_sug = calcular_precio_sugerido(costo_total)
                        c_m4.metric("Precio Venta Sugerido", f"${precio_sug:,.2f}")

                        if detalles_list:
                            df_det = pd.DataFrame(detalles_list)
                            st.dataframe(
                                df_det,
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
    # 2. CREAR NUEVA RECETA (+ SEPARACIÓN DE PACKAGING)
    # ---------------------------------------------------------
    with tab_nueva:
        st.subheader("➕ Diseñar Receta")

        res_ins = supabase.table("insumos").select("*").order("nombre").execute()
        insumos = res_ins.data or []

        if not insumos:
            st.warning("⚠️ Debes cargar insumos en el inventario antes de armar recetas.")
            return

        # Separación de diccionarios de insumos
        insumos_comestibles = {i["nombre"]: i for i in insumos if i.get("rubro") != NOMBRE_RUBRO_PACKAGING}
        insumos_packaging = {i["nombre"]: i for i in insumos if i.get("rubro") == NOMBRE_RUBRO_PACKAGING}

        # Inicialización de borradores
        if "borrador_ingredientes" not in st.session_state:
            st.session_state.borrador_ingredientes = []
        if "borrador_packaging" not in st.session_state:
            st.session_state.borrador_packaging = []

        # Datos Generales
        c1, c2, c3 = st.columns([3, 1, 1])
        r_nombre = c1.text_input("Nombre de la Receta / Producto *", placeholder="Ej. Torta Pasta Frola")
        r_rendimiento = c2.number_input("Porciones / Rendimiento por Lote", min_value=1, value=1)
        r_tiempo = c3.number_input("Tiempo (Mins)", min_value=0, value=45)
        r_desc = st.text_area("Descripción / Preparación", placeholder="Notas del chef...")

        st.markdown("---")
        
        # --- BLOQUE 1: INGREDIENTES COMESTIBLES ---
        st.markdown("#### 🥣 1. Ingredientes de la Preparación")
        if insumos_comestibles:
            col_i1, col_i2, col_i3 = st.columns([4, 2, 2])
            ins_sel_nombre = col_i1.selectbox("Seleccionar Ingrediente Comestible", list(insumos_comestibles.keys()))
            ins_obj = insumos_comestibles[ins_sel_nombre]

            cant_ingrediente = col_i2.number_input(
                f"Cantidad ({ins_obj['unidad_medida']})", min_value=0.01, step=1.0, format="%.2f", key="cant_ing"
            )
            
            if col_i3.button("➕ Añadir Ingrediente", use_container_width=True):
                costo_u = float(ins_obj["costo_unidad"] or 0)
                st.session_state.borrador_ingredientes.append({
                    "insumo_id": ins_obj["id"],
                    "nombre": ins_obj["nombre"],
                    "rubro": ins_obj.get("rubro", "Comestible"),
                    "cantidad": cant_ingrediente,
                    "unidad": ins_obj["unidad_medida"],
                    "costo_u": costo_u,
                    "subtotal": cant_ingrediente * costo_u
                })
                st.rerun()
        else:
            st.info("No tienes ingredientes comestibles registrados aún.")

        if st.session_state.borrador_ingredientes:
            df_ing = pd.DataFrame(st.session_state.borrador_ingredientes)
            st.dataframe(
                df_ing[["nombre", "rubro", "cantidad", "unidad", "costo_u", "subtotal"]],
                column_config={
                    "costo_u": st.column_config.NumberColumn("Costo U. ($)", format="$%.2f"),
                    "subtotal": st.column_config.NumberColumn("Subtotal ($)", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")

        # --- BLOQUE 2: PACKAGING Y EMPAQUE ---
        st.markdown("#### 📦 2. Packaging y Presentación")
        if insumos_packaging:
            col_p1, col_p2, col_p3 = st.columns([4, 2, 2])
            pkg_sel_nombre = col_p1.selectbox("Seleccionar Elemento de Packaging", list(insumos_packaging.keys()))
            pkg_obj = insumos_packaging[pkg_sel_nombre]

            cant_pkg = col_p2.number_input(
                f"Cantidad ({pkg_obj['unidad_medida']})", min_value=0.01, step=1.0, format="%.2f", key="cant_pkg"
            )
            
            if col_p3.button("➕ Añadir Packaging", use_container_width=True):
                costo_u = float(pkg_obj["costo_unidad"] or 0)
                st.session_state.borrador_packaging.append({
                    "insumo_id": pkg_obj["id"],
                    "nombre": pkg_obj["nombre"],
                    "rubro": NOMBRE_RUBRO_PACKAGING,
                    "cantidad": cant_pkg,
                    "unidad": pkg_obj["unidad_medida"],
                    "costo_u": costo_u,
                    "subtotal": cant_pkg * costo_u
                })
                st.rerun()
        else:
            st.info("No tienes insumos asignados al rubro 'Empaque y Descartables'.")

        if st.session_state.borrador_packaging:
            df_pkg = pd.DataFrame(st.session_state.borrador_packaging)
            st.dataframe(
                df_pkg[["nombre", "cantidad", "unidad", "costo_u", "subtotal"]],
                column_config={
                    "costo_u": st.column_config.NumberColumn("Costo U. ($)", format="$%.2f"),
                    "subtotal": st.column_config.NumberColumn("Subtotal ($)", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

        # --- CÁLCULOS Y RESUMEN FINALES ---
        todos_los_items = st.session_state.borrador_ingredientes + st.session_state.borrador_packaging

        if todos_los_items:
            subtotal_ingredientes = sum(item["subtotal"] for item in st.session_state.borrador_ingredientes)
            subtotal_packaging = sum(item["subtotal"] for item in st.session_state.borrador_packaging)
            total_receta = subtotal_ingredientes + subtotal_packaging
            
            precio_sugerido_calculado = calcular_precio_sugerido(total_receta)

            st.markdown("---")
            st.markdown("#### 💰 Desglose de Costos y Precio de Venta")

            col_met1, col_met2, col_met3, col_met4 = st.columns(4)
            col_met1.metric("Costo Ingredientes", f"${subtotal_ingredientes:,.2f}")
            col_met2.metric("Costo Packaging", f"${subtotal_packaging:,.2f}")
            col_met3.metric("Costo Total Lote", f"${total_receta:,.2f}")
            col_met4.metric("Precio Sugerido (100% Margen)", f"${precio_sugerido_calculado:,.2f}")

            precio_venta_final = st.number_input(
                "Precio Venta Inicial Final ($)",
                min_value=0.0,
                value=precio_sugerido_calculado,
                step=100.0,
                format="%.2f",
                help="Puedes modificar manualmente este precio antes de guardar."
            )

            cb1, cb2 = st.columns(2)
            if cb1.button("❌ Vaciar Borrador", use_container_width=True):
                st.session_state.borrador_ingredientes = []
                st.session_state.borrador_packaging = []
                st.rerun()

            if cb2.button("💾 Guardar Receta y Alta en Catálogo", type="primary", use_container_width=True):
                if not r_nombre.strip():
                    st.error("Ingresa el nombre de la receta.")
                else:
                    try:
                        # A) Guardar Receta
                        rec_res = supabase.table("recetas").insert({
                            "nombre": r_nombre.strip(),
                            "descripcion": r_desc.strip(),
                            "rendimiento_porciones": r_rendimiento,
                            "tiempo_preparacion_min": r_tiempo
                        }).execute()

                        receta_id = rec_res.data[0]["id"]

                        # B) Guardar Todos los Detalles (Ingredientes + Packaging)
                        for item in todos_los_items:
                            supabase.table("receta_detalles").insert({
                                "receta_id": receta_id,
                                "insumo_id": item["insumo_id"],
                                "cantidad": item["cantidad"]
                            }).execute()

                        # C) Auto-crear producto en el catálogo
                        supabase.table("productos").insert({
                            "nombre": r_nombre.strip(),
                            "receta_id": receta_id,
                            "categoria": "Tortas",
                            "precio_venta": precio_venta_final,
                            "stock_actual": 0.0,
                            "activo": True
                        }).execute()

                        st.success(f"🎉 ¡Receta y Producto **'{r_nombre}'** guardados con éxito!")
                        st.session_state.borrador_ingredientes = []
                        st.session_state.borrador_packaging = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    # ---------------------------------------------------------
    # 3. REGISTRAR PRODUCCIÓN
    # ---------------------------------------------------------
    with tab_producir:
        st.subheader("👨‍🍳 Cocinar / Producir Lotes")
        st.caption("Al confirmar, se descontarán tanto las materias primas como el packaging utilizado.")

        try:
            res_rec = (
                supabase.table("recetas")
                .select("*, receta_detalles(*, insumos(*))")
                .order("nombre")
                .execute()
            )
            recetas_prod = res_rec.data or []

            if recetas_prod:
                dict_r_prod = {r["nombre"]: r for r in recetas_prod}
                r_seleccionada = st.selectbox("Seleccionar Receta a Cocinar", list(dict_r_prod.keys()))
                receta_obj = dict_r_prod[r_seleccionada]

                cp1, cp2 = st.columns(2)
                lotes = cp1.number_input("Cantidad de Tandas / Lotes a Cocinar", min_value=1, value=1)
                porciones_totales = lotes * (receta_obj["rendimiento_porciones"] or 1)
                cp2.metric("Unidades/Porciones Producidas", porciones_totales)

                # Comprobar Stock
                st.markdown("##### 🔍 Verificación de Stock (Ingredientes + Packaging)")
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

                        rubro_ins = ins.get("rubro", "")
                        tipo_label = "📦 Packaging" if rubro_ins == NOMBRE_RUBRO_PACKAGING else "🥣 Ingrediente"

                        items_produccion.append({
                            "insumo_id": ins["id"],
                            "tipo": tipo_label,
                            "nombre": ins["nombre"],
                            "requerido": cant_requerida,
                            "stock_actual": stock_actual,
                            "unidad": ins["unidad_medida"],
                            "estado": "✅ OK" if ok else "❌ Falta Stock"
                        })

                st.dataframe(
                    pd.DataFrame(items_produccion)[["tipo", "nombre", "requerido", "stock_actual", "unidad", "estado"]],
                    use_container_width=True,
                    hide_index=True
                )

                if not suficiente:
                    st.error("⚠️ No hay suficiente stock de insumos o packaging para producir estas tandas.")

                if st.button("🍳 Confirmar Producción", type="primary", disabled=not suficiente, use_container_width=True):
                    # A) Descontar Insumos y Packaging
                    for item in items_produccion:
                        nuevo_stock_insumo = item["stock_actual"] - item["requerido"]
                        supabase.table("insumos").update({"stock_actual": nuevo_stock_insumo}).eq("id", item["insumo_id"]).execute()

                    # B) Sumar Stock al Producto Terminado
                    res_p = supabase.table("productos").select("*").eq("receta_id", receta_obj["id"]).execute()
                    prods_asociados = res_p.data or []

                    if prods_asociados:
                        prod_target = prods_asociados[0]
                        stock_prod_actual = float(prod_target.get("stock_actual") or 0.0)
                        nuevo_stock_prod = stock_prod_actual + porciones_totales
                        
                        supabase.table("productos").update({"stock_actual": nuevo_stock_prod}).eq("id", prod_target["id"]).execute()
                        st.success(f"🎉 ¡Producción registrada! Se descontaron insumos/packaging y se sumaron **+{porciones_totales} unidades** al catálogo.")
                    else:
                        costo_lote = sum(float(d["cantidad"]) * float(d.get("insumos", {}).get("costo_unidad") or 0) for d in detalles)
                        precio_sug_fallback = calcular_precio_sugerido(costo_lote)

                        supabase.table("productos").insert({
                            "nombre": receta_obj["nombre"],
                            "receta_id": receta_obj["id"],
                            "categoria": "Tortas",
                            "precio_venta": precio_sug_fallback,
                            "stock_actual": porciones_totales,
                            "activo": True
                        }).execute()
                        st.success(f"🎉 ¡Producción registrada y producto **'{receta_obj['nombre']}'** creado en catálogo!")

                    st.rerun()
            else:
                st.info("No hay recetas disponibles.")
        except Exception as e:
            st.error(f"Error en la pantalla de producción: {e}")
