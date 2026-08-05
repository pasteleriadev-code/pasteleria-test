import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_supabase_client

supabase = get_supabase_client()

def show_modulo_proveedores():
    st.header("🚚 Gestión de Proveedores y Compras")

    # Pestañas principales calcadas a tus capturas
    tab_explorador, tab_nuevo, tab_modificar, tab_compras = st.tabs([
        "🔍 Explorador", 
        "➕ Nuevo Proveedor", 
        "✏️ Modificar", 
        "🛒 Cargar / Historial Compras"
    ])

    # ---------------------------------------------------------
    # 1. VER PROVEEDORES
    # ---------------------------------------------------------
    with tab_explorador:
        st.subheader("Proveedores Registrados")
        try:
            res = supabase.table("proveedores").select("*").order("razon_social").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(
                    df[["razon_social", "cuit", "telefono", "condicion_fiscal", "direccion", "rubros"]],
                    column_config={
                        "razon_social": "Razón Social",
                        "cuit": "CUIT",
                        "telefono": "Teléfono",
                        "condicion_fiscal": "Condición Fiscal",
                        "direccion": "Dirección",
                        "rubros": "Rubros"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay proveedores dados de alta.")
        except Exception as e:
            st.error(f"Error al cargar proveedores: {e}")

    # ---------------------------------------------------------
    # 2. DAR DE ALTA PROVEEDORES (Campos exactos de tu imagen)
    # ---------------------------------------------------------
    with tab_nuevo:
        # Sugerencia estética de ID como en tu imagen
        st.info("💡 Completá los datos del nuevo proveedor")
        
        with st.form("form_nuevo_proveedor", clear_on_submit=True):
            col1, col2 = st.columns(2)
            razon_social = col1.text_input("Razón Social *")
            telefono = col2.text_input("Teléfono")

            col3, col4 = st.columns(2)
            cuit = col3.text_input("CUIT (Formato: XX-XXXXXXXX-X)")
            condicion_fiscal = col4.selectbox(
                "Condición Fiscal", 
                ["Responsable Inscripto", "Monotributo", "Exento", "Consumidor Final"]
            )

            direccion = st.text_input("Dirección")
            rubros = st.text_input("Asociar Rubros", placeholder="Ej. Lácteos, Harinas, Empaques")

            submitted = st.form_submit_button("Guardar Proveedor", use_container_width=True)

            if submitted:
                if not razon_social.strip():
                    st.error("La Razón Social es obligatoria.")
                else:
                    nuevo_prov = {
                        "razon_social": razon_social.strip(),
                        "cuit": cuit.strip(),
                        "telefono": telefono.strip(),
                        "condicion_fiscal": condicion_fiscal,
                        "direccion": direccion.strip(),
                        "rubros": rubros.strip()
                    }
                    try:
                        supabase.table("proveedores").insert(nuevo_prov).execute()
                        st.success(f"¡Proveedor '{razon_social}' registrado exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar proveedor: {e}")

    # ---------------------------------------------------------
    # 3. MODIFICAR DATOS DE PROVEEDORES
    # ---------------------------------------------------------
    with tab_modificar:
        st.subheader("Editar Proveedor Existente")
        try:
            res_prov = supabase.table("proveedores").select("*").order("razon_social").execute()
            listado_provs = res_prov.data

            if listado_provs:
                dict_provs = {p["razon_social"]: p for p in listado_provs}
                prov_seleccionado = st.selectbox("Seleccionar Proveedor a Modificar:", list(dict_provs.keys()))
                
                datos_actuales = dict_provs[prov_seleccionado]

                with st.form("form_edit_proveedor"):
                    col1, col2 = st.columns(2)
                    edit_razon = col1.text_input("Razón Social", value=datos_actuales["razon_social"])
                    edit_tel = col2.text_input("Teléfono", value=datos_actuales.get("telefono", ""))

                    col3, col4 = st.columns(2)
                    edit_cuit = col3.text_input("CUIT", value=datos_actuales.get("cuit", ""))
                    
                    opciones_cf = ["Responsable Inscripto", "Monotributo", "Exento", "Consumidor Final"]
                    idx_cf = opciones_cf.index(datos_actuales.get("condicion_fiscal", "Responsable Inscripto"))
                    edit_cf = col4.selectbox("Condición Fiscal", opciones_cf, index=idx_cf)

                    edit_dir = st.text_input("Dirección", value=datos_actuales.get("direccion", ""))
                    edit_rubros = st.text_input("Rubros", value=datos_actuales.get("rubros", ""))

                    if st.form_submit_button("Actualizar Cambios", use_container_width=True):
                        update_data = {
                            "razon_social": edit_razon,
                            "cuit": edit_cuit,
                            "telefono": edit_tel,
                            "condicion_fiscal": edit_cf,
                            "direccion": edit_dir,
                            "rubros": edit_rubros
                        }
                        supabase.table("proveedores").update(update_data).eq("id", datos_actuales["id"]).execute()
                        st.success("¡Datos actualizados correctamente!")
                        st.rerun()
            else:
                st.info("No hay proveedores disponibles para editar.")
        except Exception as e:
            st.error(f"Error: {e}")

    # ---------------------------------------------------------
    # 4. CARGAR FACTURA DE COMPRA E HISTORIAL (Basado en 2da captura)
    # ---------------------------------------------------------
    with tab_compras:
        with st.expander("📁 Ver / Ocultar Historial de Compras", expanded=False):
            try:
                historial = supabase.table("compras").select("*, proveedores(razon_social)").order("fecha_factura", ascending=False).execute()
                if historial.data:
                    df_h = pd.DataFrame(historial.data)
                    df_h["proveedor"] = df_h["proveedores"].apply(lambda x: x["razon_social"] if x else "N/A")
                    st.dataframe(
                        df_h[["fecha_factura", "proveedor", "punto_venta", "numero_factura", "metodo_pago", "monto_total"]],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No hay compras registradas aún.")
            except Exception as e:
                st.error(f"Error al cargar historial: {e}")

        st.subheader("📄 Datos de la Factura Actual")

        # Obtener proveedores para el selectbox
        res_p = supabase.table("proveedores").select("id, razon_social").execute()
        provs = res_p.data

        if not provs:
            st.warning("⚠️ Primero debes dar de alta al menos un Proveedor en la pestaña 'Nuevo Proveedor'.")
            return

        dict_provs_compra = {p["razon_social"]: p["id"] for p in provs}

        # Formulario de cabecera de la factura (Diseño exacto a la captura)
        c1, c2, c3, c4 = st.columns([3, 1.5, 2, 2])
        prov_nombre = c1.selectbox("Proveedor", list(dict_provs_compra.keys()))
        pv = c2.text_input("Punto Venta", value="00001", max_chars=5)
        nro_fac = c3.text_input("N° Factura", value="00000001", max_chars=8)
        metodo_pago = c4.selectbox("Método de Pago", ["Contado", "Transferencia", "Tarjeta Crédito/Débito", "Cuenta Corriente"])

        fecha_fac = st.date_input("Fecha de Factura", value=datetime.today())

        st.markdown("---")
        st.subheader("🔍 Añadir Insumos a la Compra")

        # Obtener insumos
        res_ins = supabase.table("insumos").select("*").order("nombre").execute()
        insumos = res_ins.data

        if not insumos:
            st.warning("⚠️ No hay insumos registrados en el inventario. Agrega insumos primero.")
            return

        dict_insumos = {i["nombre"]: i for i in insumos}

        # Inicializar carrito de compras en la sesión de Streamlit
        if "carrito_compra" not in st.session_state:
            st.session_state.carrito_compra = []

        col_ins, col_cant, col_precio, col_btn = st.columns([4, 2, 2, 2])
        ins_sel_nombre = col_ins.selectbox("Escriba para buscar producto/insumo...", list(dict_insumos.keys()))
        ins_objeto = dict_insumos[ins_sel_nombre]

        cant_comprada = col_cant.number_input(f"Cantidad ({ins_objeto['unidad_medida']})", min_value=0.01, step=1.0)
        precio_unitario = col_precio.number_input("Precio Unitario ($)", min_value=0.0, step=10.0, format="%.2f")

        if col_btn.button("➕ Agregar Item", use_container_width=True):
            subtotal = cant_comprada * precio_unitario
            st.session_state.carrito_compra.append({
                "insumo_id": ins_objeto["id"],
                "nombre": ins_objeto["nombre"],
                "cantidad": cant_comprada,
                "unidad": ins_objeto["unidad_medida"],
                "precio_unitario": precio_unitario,
                "subtotal": subtotal
            })
            st.rerun()

        # Mostrar Tabla de Items en la Factura actual
        if st.session_state.carrito_compra:
            st.markdown("### 🛒 Detalle de la Compra")
            df_carrito = pd.DataFrame(st.session_state.carrito_compra)
            st.dataframe(df_carrito[["nombre", "cantidad", "unidad", "precio_unitario", "subtotal"]], use_container_width=True, hide_index=True)

            total_compra = df_carrito["subtotal"].sum()
            st.markdown(f"### **Total Factura: ${total_compra:,.2f}**")

            col_cancel, col_confirm = st.columns(2)
            if col_cancel.button("❌ Vaciar Carrito", use_container_width=True):
                st.session_state.carrito_compra = []
                st.rerun()

            if col_confirm.button("✅ Registrar Factura y Actualizar Stock", type="primary", use_container_width=True):
                try:
                    # 1. Registrar Cabecera Factura
                    compra_payload = {
                        "proveedor_id": dict_provs_compra[prov_nombre],
                        "punto_venta": pv,
                        "numero_factura": nro_fac,
                        "fecha_factura": str(fecha_fac),
                        "metodo_pago": metodo_pago,
                        "monto_total": total_compra
                    }
                    compra_res = supabase.table("compras").insert(compra_payload).execute()
                    compra_id = compra_res.data[0]["id"]

                    # 2. Registrar Detalles y Actualizar Stock/Costo en Insumos
                    for item in st.session_state.carrito_compra:
                        detalle_payload = {
                            "compra_id": compra_id,
                            "insumo_id": item["insumo_id"],
                            "cantidad": item["cantidad"],
                            "precio_unitario": item["precio_unitario"]
                        }
                        supabase.table("compra_detalles").insert(detalle_payload).execute()

                        # Aumentar stock y actualizar precio de costo del insumo
                        ins_id = item["insumo_id"]
                        ins_actual = supabase.table("insumos").select("stock_actual").eq("id", ins_id).single().execute().data
                        nuevo_stock = float(ins_actual["stock_actual"]) + float(item["cantidad"])

                        supabase.table("insumos").update({
                            "stock_actual": nuevo_stock,
                            "costo_unidad": item["precio_unitario"] # Actualiza el precio de costo al último precio comprado
                        }).eq("id", ins_id).execute()

                    st.success("🎉 ¡Compra registrada con éxito! El stock y los costos de insumos han sido actualizados.")
                    st.session_state.carrito_compra = []
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al procesar la factura: {e}")
