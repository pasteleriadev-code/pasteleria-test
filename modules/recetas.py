import streamlit as st
import pandas as pd
from utils import get_supabase_client

supabase = get_supabase_client()

def show_modulo_recetas():
    st.header("🧾 Recetario y Escandallos (BOM)")

    tab_catalogo, tab_nueva, tab_producir = st.tabs([
        "📖 Catálogo de Recetas", 
        "➕ Diseñar / Crear Receta", 
        "👨‍🍳 Registrar Producción (Descontar Stock)"
    ])

    # ---------------------------------------------------------
    # 1. CATÁLOGO DE RECETAS Y CÁLCULO DE COSTOS
    # ---------------------------------------------------------
    with tab_catalogo:
        st.subheader("Recetas Registradas")
        try:
            # Traer recetas con sus detalles e insumos
            res_recetas = supabase.table("recetas").select("*, receta_detalles(*, insumos(*))").order("nombre").execute()
            recetas = res_recetas.data

            if recetas:
                for r in recetas:
                    # Calcular costo total acumulando (cantidad * costo_unidad del insumo)
                    costo_total_materia_prima = 0.0
                    detalles_list = []

                    for d in r.get("receta_detalles", []):
                        ins = d.get("insumos")
                        if ins:
                            cant = float(d["cantidad"])
                            costo_unit = float(ins["costo_unidad"])
                            subtotal = cant * costo_unit
                            costo_total_materia_prima += subtotal
                            detalles_list.append({
                                "Ingrediente": ins["nombre"],
                                "Cantidad": cant,
                                "Unidad": ins["unidad_medida"],
                                "Costo Unitario ($)": costo_unit,
                                "Subtotal ($)": subtotal
                            })

                    rendimiento = r["rendimiento_porciones"] or 1
                    costo_por_porcion = costo_total_materia_prima / rendimiento if rendimiento > 0 else 0.0

                    # Desplegable por receta
                    with st.expander(f"🎂 {r['nombre']} — Costo Total: ${costo_total_materia_prima:,.2f} | Rendimiento: {rendimiento} porción(es)"):
                        st.markdown(f"**Descripción:** {r.get('descripcion') or 'Sin descripción'}")
                        st.markdown(f"**Tiempo de preparación:** {r.get('tiempo_preparacion_min') or 0} mins")
                        
                        m1, m2 = st.columns(2)
                        m1.metric("Costo Total Materia Prima", f"${costo_total_materia_prima:,.2f}")
                        m2.metric("Costo por Porción / Unidad", f"${costo_por_porcion:,.2f}")

                        if detalles_list:
                            st.write("**Ingredientes y Escandallo:**")
                            df_det = pd.DataFrame(detalles_list)
                            st.dataframe(
                                df_det,
                                column_config={
                                    "Costo Unitario ($)": st.column_config.NumberColumn(format="$%.4f"),
                                    "Subtotal ($)": st.column_config.NumberColumn(format="$%.2f")
                                },
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.warning("Esta receta no tiene ingredientes asignados aún.")

                        # Botón para eliminar receta
                        if st.button(f"🗑️ Eliminar Receta '{r['nombre']}'", key=f"del_{r['id']}"):
                            supabase.table("recetas").delete().eq("id", r["id"]).execute()
                            st.success(f"Receta '{r['nombre']}' eliminada.")
                            st.rerun()
            else:
                st.info("No hay recetas creadas. Diseña la primera en la siguiente pestaña.")
        except Exception as e:
            st.error(f"Error al cargar las recetas: {e}")

    # ---------------------------------------------------------
    # 2. DISEÑADOR / CREACIÓN DE RECETAS
    # ---------------------------------------------------------
    with tab_nueva:
        st.subheader("➕ Diseñador de Recetas")
        st.caption("Arma la composición de tu producto agregando insumos del inventario.")

        # Obtener lista de insumos disponibles
        res_ins = supabase.table("insumos").select("*").order("nombre").execute()
        insumos = res_ins.data

        if not insumos:
            st.warning("⚠️ Debes dar de alta insumos en el modulo de Inventario antes de crear una receta.")
            return

        dict_insumos = {i["nombre"]: i for i in insumos}

        # Estado del borrador de la receta en sesión
        if "borrador_ingredientes" not in st.session_state:
            st.session_state.borrador_ingredientes = []

        # Datos Generales
        col_r1, col_r2, col_r3 = st.columns([3, 1, 1])
        receta_nombre = col_r1.text_input("Nombre de la Receta *", placeholder="Ej. Torta Red Velvet 24cm")
        rendimiento = col_r2.number_input("Rendimiento (Porciones/Unidades)", min_value=1, value=1)
        tiempo_prep = col_r3.number_input("Tiempo (Mins)", min_value=0, value=60)
        descripcion = st.text_area("Descripción / Notas de Preparación", placeholder="Pasos clave o instrucciones...")

        st.markdown("---")
        st.markdown("### 🥗 Agregar Ingredientes")

        col_i1, col_i2, col_i3 = st.columns([4, 2, 2])
        ins_nombre = col_i1.selectbox("Seleccionar Insumo", list(dict_insumos.keys()))
        ins_obj = dict_insumos[ins_nombre]

        cant_requerida = col_i2.number_input(f"Cantidad ({ins_obj['unidad_medida']})", min_value=0.01, step=10.0, format="%.2f")
        costo_unit = float(ins_obj["costo_unidad"])

        if col_i3.button("➕ Añadir Ingrediente", use_container_width=True):
            subtotal = cant_requerida * costo_unit
            st.session_state.borrador_ingredientes.append({
                "insumo_id": ins_obj["id"],
                "nombre": ins_obj["nombre"],
                "cantidad": cant_requerida,
                "unidad": ins_obj["unidad_medida"],
                "costo_unitario": costo_unit,
                "subtotal": subtotal
            })
            st.rerun()

        # Tabla de ingredientes agregados al borrador
        if st.session_state.borrador_ingredientes:
            st.markdown("#### Ingredientes de la Receta Actual")
            df_borrador = pd.DataFrame(st.session_state.borrador_ingredientes)
            st.dataframe(
                df_borrador[["nombre", "cantidad", "unidad", "costo_unitario", "subtotal"]],
                column_config={
                    "costo_unitario": st.column_config.NumberColumn("Costo Unit. ($)", format="$%.4f"),
                    "subtotal": st.column_config.NumberColumn("Subtotal ($)", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

            total_receta = df_borrador["subtotal"].sum()
            costo_porcion = total_receta / rendimiento if rendimiento > 0 else 0.0

            c_met1, c_met2 = st.columns(2)
            c_met1.metric("Costo Total Estimado", f"${total_receta:,.2f}")
            c_met2.metric("Costo Por Porción", f"${costo_porcion:,.2f}")

            c_bot1, c_bot2 = st.columns(2)
            if c_bot1.button("❌ Vaciar Ingredientes", use_container_width=True):
                st.session_state.borrador_ingredientes = []
                st.rerun()

            if c_bot2.button("💾 Guardar Receta Completa", type="primary", use_container_width=True):
                if not receta_nombre.strip():
                    st.error("Por favor ingresa un nombre para la receta.")
                else:
                    try:
                        # 1. Insertar Cabecera Receta
                        rec_payload = {
                            "nombre": receta_nombre.strip(),
                            "descripcion": descripcion.strip(),
                            "rendimiento_porciones": rendimiento,
                            "tiempo_preparacion_min": tiempo_prep
                        }
                        res_rec = supabase.table("recetas").insert(rec_payload).execute()
                        receta_id = res_rec.data[0]["id"]

                        # 2. Insertar Detalle de Insumos
                        for item in st.session_state.borrador_ingredientes:
                            det_payload = {
                                "receta_id": receta_id,
                                "insumo_id": item["insumo_id"],
                                "cantidad": item["cantidad"]
                            }
                            supabase.table("receta_detalles").insert(det_payload).execute()

                        st.success(f"🎉 Receta '{receta_nombre}' creada con éxito!")
                        st.session_state.borrador_ingredientes = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar receta: {e}")

    # ---------------------------------------------------------
    # 3. REGISTRAR PRODUCCIÓN (DESCONTAR STOCK AUTOMÁTICO)
    # ---------------------------------------------------------
    with tab_producir:
        st.subheader("👨‍🍳 Registrar Tanda de Producción")
        st.caption("Selecciona una receta y la cantidad de lotes producidos para descontar los insumos del inventario automáticamente.")

        try:
            res_r = supabase.table("recetas").select("*, receta_detalles(*, insumos(*))").order("nombre").execute()
            recetas_prod = res_r.data

            if recetas_prod:
                dict_recetas_prod = {r["nombre"]: r for r in recetas_prod}
                receta_sel_nombre = st.selectbox("Seleccionar Receta a Cocinar", list(dict_recetas_prod.keys()))
                receta_obj = dict_recetas_prod[receta_sel_nombre]

                col_p1, col_p2 = st.columns(2)
                lotes = col_p1.number_input("Cantidad de Tandas / Lotes a Producir", min_value=1, value=1)
                porciones_totales = lotes * (receta_obj["rendimiento_porciones"] or 1)
                col_p2.metric("Total Porciones/Unidades Producidas", porciones_totales)

                # Verificar insumos necesarios vs stock actual
                st.markdown("#### 🔍 Verificación de Stock para la Producción")
                detalles = receta_obj.get("receta_detalles", [])
                
                stock_suficiente = True
                resumen_produccion = []

                for d in detalles:
                    ins = d.get("insumos")
                    if ins:
                        cant_necesaria_unitaria = float(d["cantidad"])
                        cant_total_requerida = cant_necesaria_unitaria * lotes
                        stock_actual = float(ins["stock_actual"])
                        diferencia = stock_actual - cant_total_requerida
                        
                        alerta = "✅ OK" if diferencia >= 0 else "❌ STOCK INSUFICIENTE"
                        if diferencia < 0:
                            stock_suficiente = False

                        resumen_produccion.append({
                            "insumo_id": ins["id"],
                            "nombre": ins["nombre"],
                            "requerido": cant_total_requerida,
                            "stock_actual": stock_actual,
                            "unidad": ins["unidad_medida"],
                            "estado": alerta
                        })

                df_prod = pd.DataFrame(resumen_produccion)
                st.dataframe(
                    df_prod[["nombre", "requerido", "stock_actual", "unidad", "estado"]],
                    column_config={
                        "requerido": st.column_config.NumberColumn("Requerido Total", format="%.2f"),
                        "stock_actual": st.column_config.NumberColumn("Stock Actual", format="%.2f"),
                    },
                    use_container_width=True,
                    hide_index=True
                )

                if not stock_suficiente:
                    st.error("⚠️ No hay suficiente stock de materias primas para cocinar esta cantidad de lotes.")
                
                if st.button("🍳 Confirmar Producción y Descontar Stock", type="primary", disabled=not stock_suficiente, use_container_width=True):
                    try:
                        # Descontar stock de cada insumo
                        for item in resumen_produccion:
                            nuevo_stock = item["stock_actual"] - item["requerido"]
                            supabase.table("insumos").update({"stock_actual": nuevo_stock}).eq("id", item["insumo_id"]).execute()

                        st.success(f"🎉 ¡Producción de '{receta_sel_nombre}' registrada! Se ha descontado la materia prima de Supabase.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al procesar la producción: {e}")
            else:
                st.info("No hay recetas disponibles para producción.")
        except Exception as e:
            st.error(f"Error: {e}")
