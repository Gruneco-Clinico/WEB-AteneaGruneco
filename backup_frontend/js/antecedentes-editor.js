/**
 * Editor de Antecedentes Médicos - Versión Optimizada
 * Maneja los 13 tipos de antecedentes médicos de forma eficiente
 */

class AntecedentesEditor {
    constructor() {
        this.contadores = {
            patologicos: 0,
            quirurgicos: 0,
            farmacologicos: 0,
            toxicos: 0,
            familiares: 0,
            alergicos: 0,
            traumaticos: 0,
            gineco: 0,
            epidemiologicos: 0,
            ets: 0,
            hospitalizaciones: 0,
            inmunizaciones: 0,
            transfusionales: 0,
        };

        this.datosExamen = null;
        this.modoEdicion = false;
        this.cambiosNoGuardados = false;
        this.autosaveInterval = null;

        this.init();
    }

    init() {
        console.log('🚀 Inicializando AntecedentesEditor...');

        // Cargar datos del servidor
        this.cargarDatosServidor();

        // Configurar eventos
        this.configurarEventos();

        // Configurar auto-guardado
        this.configurarAutoguardado();

        // Cargar datos existentes
        this.cargarDatosExistentes();

        // Exponer funciones globales
        this.exponerFuncionesGlobales();

        console.log('✅ AntecedentesEditor inicializado correctamente');
    }

    cargarDatosServidor() {
        try {
            // Intentar cargar datos del template Django
            const scriptElement = document.querySelector('script[data-antecedentes]');
            if (scriptElement) {
                this.datosExamen = JSON.parse(scriptElement.dataset.antecedentes);
                this.modoEdicion = scriptElement.dataset.modoEdicion === 'true';
            }
        } catch (error) {
            console.warn('⚠️ No se pudieron cargar datos del servidor:', error);
            this.datosExamen = null;
            this.modoEdicion = false;
        }

        console.log('📋 Datos del servidor:', {
            modoEdicion: this.modoEdicion,
            tienedatos: !!this.datosExamen
        });
    }

    configurarEventos() {
        // Control del checkbox principal
        const checkboxPrincipal = document.getElementById('tiene_antecedentes');
        if (checkboxPrincipal) {
            checkboxPrincipal.addEventListener('change', (e) => {
                this.toggleVisibilidadSecciones(e.target.checked);
            });
        }

        // Detectar cambios en el formulario
        document.addEventListener('input', (e) => {
            if (e.target.matches('input, select, textarea')) {
                this.cambiosNoGuardados = true;
                this.mostrarIndicadorCambios(true);
            }
        });

        document.addEventListener('change', (e) => {
            if (e.target.matches('input[type="checkbox"], select')) {
                this.cambiosNoGuardados = true;
                this.mostrarIndicadorCambios(true);
            }
        });

        // Manejo del envío del formulario
        const form = document.getElementById('formAntecedentes');
        if (form) {
            form.addEventListener('submit', (e) => {
                this.manejarEnvioFormulario(e);
            });
        }

        // Botones de utilidad
        const btnValidar = document.querySelector('[onclick="validarFormulario()"]');
        if (btnValidar) {
            btnValidar.addEventListener('click', () => this.validarFormulario());
        }

        const btnLimpiar = document.querySelector('[onclick="limpiarFormulario()"]');
        if (btnLimpiar) {
            btnLimpiar.addEventListener('click', () => this.limpiarFormulario());
        }

        // Prevenir pérdida de datos
        window.addEventListener('beforeunload', (e) => {
            if (this.cambiosNoGuardados) {
                e.preventDefault();
                e.returnValue = '¿Estás seguro de que quieres salir? Los cambios no guardados se perderán.';
                return e.returnValue;
            }
        });
    }

    configurarAutoguardado() {
        // Auto-guardado cada 2 minutos
        this.autosaveInterval = setInterval(() => {
            if (this.cambiosNoGuardados) {
                this.guardarBorrador();
            }
        }, 120000);

        // Mostrar indicador de auto-guardado
        this.crearIndicadorAutoguardado();
    }

    crearIndicadorAutoguardado() {
        const indicator = document.createElement('div');
        indicator.id = 'autosave-indicator';
        indicator.className = 'position-fixed bg-success text-white p-2 rounded shadow';
        indicator.style.cssText = 'bottom: 20px; right: 20px; z-index: 9999; display: none; font-size: 0.875rem;';
        indicator.innerHTML = '<i class="fas fa-save mr-2"></i>Guardado automáticamente';
        document.body.appendChild(indicator);
    }

    mostrarIndicadorCambios(mostrar) {
        const indicator = document.getElementById('cambios-indicator') || this.crearIndicadorCambios();
        if (mostrar) {
            indicator.style.display = 'block';
        } else {
            indicator.style.display = 'none';
        }
    }

    crearIndicadorCambios() {
        const indicator = document.createElement('div');
        indicator.id = 'cambios-indicator';
        indicator.className = 'position-fixed bg-warning text-dark p-2 rounded shadow';
        indicator.style.cssText = 'bottom: 70px; right: 20px; z-index: 9999; display: none; font-size: 0.875rem;';
        indicator.innerHTML = '<i class="fas fa-exclamation-triangle mr-2"></i>Cambios sin guardar';
        document.body.appendChild(indicator);
        return indicator;
    }

    async guardarBorrador() {
        try {
            const datos = this.recopilarTodosDatos();

            // Aquí podrías implementar una llamada AJAX para guardar borrador
            console.log('💾 Guardando borrador...', datos);

            // Simular guardado exitoso
            this.mostrarMensajeAutoguardado();
            this.cambiosNoGuardados = false;
            this.mostrarIndicadorCambios(false);

        } catch (error) {
            console.error('❌ Error en auto-guardado:', error);
        }
    }

    mostrarMensajeAutoguardado() {
        const indicator = document.getElementById('autosave-indicator');
        if (indicator) {
            indicator.style.display = 'block';
            setTimeout(() => {
                indicator.style.display = 'none';
            }, 3000);
        }
    }

    toggleVisibilidadSecciones(mostrar) {
        const tabsContainer = document.getElementById('antecedentesTabs');
        const tabContent = document.querySelector('.tab-content');

        if (tabsContainer && tabContent) {
            const displayValue = mostrar ? 'block' : 'none';
            tabsContainer.parentElement.style.display = displayValue;
        }
    }

    // =============== TEMPLATES PARA CADA TIPO DE ANTECEDENTE ===============

    getTemplatePatologicos(indice) {
        return `
        <div class="card mb-3 border-left-primary" data-index="${indice}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-disease text-primary mr-2"></i>
              Antecedente Patológico #${indice + 1}
            </h6>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'patologicos')" title="Duplicar">
                <i class="fas fa-copy"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'patologicos')" title="Eliminar">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Tipo de patología *</label>
                  <select class="form-control" name="patologicos[${indice}][tipo_patologia]" required>
                    <option value="">Seleccione una opción...</option>
                    <option value="hipertension">Hipertensión arterial</option>
                    <option value="dislipidemia">Dislipidemia</option>
                    <option value="diabetes">Diabetes</option>
                    <option value="cancer">Cáncer</option>
                    <option value="enfermedad_renal">Enfermedad Renal</option>
                    <option value="enfermedad_cardiaca">Enfermedad Cardíaca</option>
                    <option value="enfermedad_respiratoria">Enfermedad Respiratoria</option>
                    <option value="enfermedad_hepatica">Enfermedad Hepática</option>
                    <option value="enfermedad_tiroidea">Enfermedad Tiroidea</option>
                    <option value="enfermedad_cerebrovascular">Enfermedad Cerebrovascular</option>
                    <option value="enfermedad_psiquiatrica">Enfermedad Psiquiátrica</option>
                    <option value="cefalea">Cefalea</option>
                    <option value="crisis_convulsivas">Crisis Convulsivas</option>
                    <option value="enfermedades_neurodegenerativas">Enfermedades Neurodegenerativas</option>
                    <option value="retardo_mental">Retardo Mental</option>
                    <option value="dificultades_aprendizaje">Dificultades del Aprendizaje</option>
                    <option value="sindrome_down">Síndrome de Down</option>
                    <option value="trastorno_desarrollo">Trastorno del desarrollo psicomotor</option>
                    <option value="deficit_atencion">Déficit de atención o hiperactividad</option>
                    <option value="otros">Otros</option>
                  </select>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha de inicio *</label>
                  <input type="date" class="form-control" name="patologicos[${indice}][fecha_inicio]" required max="${new Date().toISOString().split('T')[0]}">
                </div>
              </div>
            </div>
            
            <div class="row" id="descripcion-otros-${indice}" style="display: none;">
              <div class="col-md-12">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Descripción (si es otros) *</label>
                  <input type="text" class="form-control" name="patologicos[${indice}][descripcion_otros]" placeholder="Especifique la patología">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="tratamiento_pat_${indice}" name="patologicos[${indice}][ha_recibido_tratamiento]" value="true">
                    <label class="custom-control-label" for="tratamiento_pat_${indice}">¿Ha recibido tratamiento?</label>
                  </div>
                </div>
                <div class="form-group tratamiento-details" id="tratamiento-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detalle del tratamiento</label>
                  <textarea class="form-control" name="patologicos[${indice}][detalle_tratamiento]" rows="2" placeholder="Describa el tratamiento recibido..."></textarea>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="complicaciones_pat_${indice}" name="patologicos[${indice}][tiene_complicaciones]" value="true">
                    <label class="custom-control-label" for="complicaciones_pat_${indice}">¿Tiene complicaciones?</label>
                  </div>
                </div>
                <div class="form-group complicaciones-details" id="complicaciones-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detalle de complicaciones</label>
                  <textarea class="form-control" name="patologicos[${indice}][detalle_complicaciones]" rows="2" placeholder="Describa las complicaciones..."></textarea>
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="activo_pat_${indice}" name="patologicos[${indice}][activo]" value="true" checked>
                    <label class="custom-control-label" for="activo_pat_${indice}">¿Activo actualmente?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group fecha-finalizacion" id="fecha-finalizacion-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Fecha de finalización</label>
                  <input type="date" class="form-control" name="patologicos[${indice}][fecha_finalizacion]">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-12">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="patologicos[${indice}][observaciones]" rows="2" placeholder="Observaciones adicionales..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    getTemplateQuirurgicos(indice) {
        return `
        <div class="card mb-3 border-left-info" data-index="${indice}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-scalpel text-info mr-2"></i>
              Antecedente Quirúrgico #${indice + 1}
            </h6>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'quirurgicos')" title="Duplicar">
                <i class="fas fa-copy"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'quirurgicos')" title="Eliminar">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-8">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Descripción de la cirugía *</label>
                  <input type="text" class="form-control" name="quirurgicos[${indice}][descripcion]" required placeholder="Tipo de procedimiento quirúrgico...">
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha de intervención *</label>
                  <input type="date" class="form-control" name="quirurgicos[${indice}][fecha_intervencion]" required max="${new Date().toISOString().split('T')[0]}">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="tratamiento_quir_${indice}" name="quirurgicos[${indice}][ha_recibido_tratamiento]" value="true">
                    <label class="custom-control-label" for="tratamiento_quir_${indice}">¿Requirió tratamiento posterior?</label>
                  </div>
                </div>
                <div class="form-group tratamiento-details" id="tratamiento-quir-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detalle del tratamiento</label>
                  <textarea class="form-control" name="quirurgicos[${indice}][detalle_tratamiento]" rows="2" placeholder="Tratamiento postoperatorio..."></textarea>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="complicaciones_quir_${indice}" name="quirurgicos[${indice}][tiene_complicaciones]" value="true">
                    <label class="custom-control-label" for="complicaciones_quir_${indice}">¿Tuvo complicaciones?</label>
                  </div>
                </div>
                <div class="form-group complicaciones-details" id="complicaciones-quir-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detalle de complicaciones</label>
                  <textarea class="form-control" name="quirurgicos[${indice}][detalle_complicaciones]" rows="2" placeholder="Complicaciones durante o después de la cirugía..."></textarea>
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="activo_quir_${indice}" name="quirurgicos[${indice}][activo]" value="true" checked>
                    <label class="custom-control-label" for="activo_quir_${indice}">¿Activo actualmente?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group fecha-finalizacion" id="fecha-quir-finalizacion-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Fecha de finalización</label>
                  <input type="date" class="form-control" name="quirurgicos[${indice}][fecha_finalizacion]">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-12">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="quirurgicos[${indice}][observaciones]" rows="2" placeholder="Observaciones adicionales..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    getTemplateFarmacologicos(indice) {
        return `
        <div class="card mb-3 border-left-success" data-index="${indice}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-pills text-success mr-2"></i>
              Antecedente Farmacológico #${indice + 1}
            </h6>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'farmacologicos')" title="Duplicar">
                <i class="fas fa-copy"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'farmacologicos')" title="Eliminar">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-8">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Descripción del medicamento/reacción *</label>
                  <input type="text" class="form-control" name="farmacologicos[${indice}][descripcion]" required placeholder="Nombre del medicamento y reacción...">
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha de inicio *</label>
                  <input type="date" class="form-control" name="farmacologicos[${indice}][fecha_inicio]" required max="${new Date().toISOString().split('T')[0]}">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="tratamiento_farm_${indice}" name="farmacologicos[${indice}][recibio_tratamiento]" value="true">
                    <label class="custom-control-label" for="tratamiento_farm_${indice}">¿Recibió tratamiento?</label>
                  </div>
                </div>
                <div class="form-group tratamiento-details" id="tratamiento-farm-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detalle del tratamiento</label>
                  <textarea class="form-control" name="farmacologicos[${indice}][detalle_tratamiento]" rows="2" placeholder="Tratamiento recibido para la reacción..."></textarea>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="complicaciones_farm_${indice}" name="farmacologicos[${indice}][tuvo_complicaciones]" value="true">
                    <label class="custom-control-label" for="complicaciones_farm_${indice}">¿Tuvo complicaciones?</label>
                  </div>
                </div>
                <div class="form-group complicaciones-details" id="complicaciones-farm-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detalle de complicaciones</label>
                  <textarea class="form-control" name="farmacologicos[${indice}][detalle_complicaciones]" rows="2" placeholder="Complicaciones presentadas..."></textarea>
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="activo_farm_${indice}" name="farmacologicos[${indice}][activo]" value="true" checked>
                    <label class="custom-control-label" for="activo_farm_${indice}">¿Está activo?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group fecha-finalizacion" id="fecha-farm-finalizacion-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Fecha de finalización</label>
                  <input type="date" class="form-control" name="farmacologicos[${indice}][fecha_finalizacion]">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-12">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="farmacologicos[${indice}][observaciones]" rows="2" placeholder="Observaciones adicionales..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    getTemplateToxicos(indice) {
        return `
        <div class="card mb-3 border-left-warning" data-index="${indice}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-smoking text-warning mr-2"></i>
              Antecedente Tóxico #${indice + 1}
            </h6>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'toxicos')" title="Duplicar">
                <i class="fas fa-copy"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'toxicos')" title="Eliminar">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Tipos de antecedente tóxico *</label>
                  <select class="form-control" name="toxicos[${indice}][tipos_toxico]" required multiple size="6">
                    <option value="tabaquismo">Tabaquismo</option>
                    <option value="alcohol">Consumo de Alcohol</option>
                    <option value="sustancias_psicoactivas">Sustancias Psicoactivas</option>
                    <option value="intoxicaciones">Intoxicaciones</option>
                    <option value="alergias_medicamentos">Alergias a Medicamentos</option>
                    <option value="otros">Otros</option>
                  </select>
                  <small class="form-text text-muted">Mantén presionado Ctrl (Cmd en Mac) para seleccionar múltiples opciones</small>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha de inicio *</label>
                  <input type="date" class="form-control" name="toxicos[${indice}][fecha_inicio]" required max="${new Date().toISOString().split('T')[0]}">
                </div>
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Descripción (otros)</label>
                  <input type="text" class="form-control" name="toxicos[${indice}][descripcion_otros]" placeholder="Especifique si seleccionó 'Otros'">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="tratamiento_tox_${indice}" name="toxicos[${indice}][ha_recibido_tratamiento]" value="true">
                    <label class="custom-control-label" for="tratamiento_tox_${indice}">¿Ha recibido tratamiento?</label>
                  </div>
                </div>
                <div class="form-group tratamiento-details" id="tratamiento-tox-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detalle del tratamiento</label>
                  <textarea class="form-control" name="toxicos[${indice}][detalle_tratamiento]" rows="2" placeholder="Tratamiento de desintoxicación o rehabilitación..."></textarea>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="complicaciones_tox_${indice}" name="toxicos[${indice}][tiene_complicaciones]" value="true">
                    <label class="custom-control-label" for="complicaciones_tox_${indice}">¿Tiene complicaciones?</label>
                  </div>
                </div>
                <div class="form-group complicaciones-details" id="complicaciones-tox-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detalle de complicaciones</label>
                  <textarea class="form-control" name="toxicos[${indice}][detalle_complicaciones]" rows="2" placeholder="Complicaciones del consumo..."></textarea>
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="activo_tox_${indice}" name="toxicos[${indice}][activo]" value="true" checked>
                    <label class="custom-control-label" for="activo_tox_${indice}">¿Activo actualmente?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group fecha-finalizacion" id="fecha-tox-finalizacion-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Fecha de finalización</label>
                  <input type="date" class="form-control" name="toxicos[${indice}][fecha_finalizacion]">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-12">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="toxicos[${indice}][observaciones]" rows="2" placeholder="Observaciones adicionales..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    getTemplateFamiliares(indice) {
        return `
        <div class="card mb-3 border-left-secondary" data-index="${indice}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-users text-secondary mr-2"></i>
              Antecedente Familiar #${indice + 1}
            </h6>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'familiares')" title="Duplicar">
                <i class="fas fa-copy"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'familiares')" title="Eliminar">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Tipo de antecedente *</label>
                  <input type="text" class="form-control" name="familiares[${indice}][tipo_antecedente]" required placeholder="Enfermedad o condición médica...">
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Parentesco *</label>
                  <select class="form-control" name="familiares[${indice}][parentesco]" required>
                    <option value="">Seleccione...</option>
                    <option value="padre">Padre</option>
                    <option value="madre">Madre</option>
                    <option value="hermano">Hermano(a)</option>
                    <option value="abuelo_paterno">Abuelo paterno</option>
                    <option value="abuela_paterna">Abuela paterna</option>
                    <option value="abuelo_materno">Abuelo materno</option>
                    <option value="abuela_materna">Abuela materna</option>
                    <option value="tio_paterno">Tío paterno</option>
                    <option value="tia_paterna">Tía paterna</option>
                    <option value="tio_materno">Tío materno</option>
                    <option value="tia_materna">Tía materna</option>
                    <option value="primo">Primo(a)</option>
                    <option value="hijo">Hijo(a)</option>
                    <option value="nieto">Nieto(a)</option>
                    <option value="otro">Otro</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-12">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="familiares[${indice}][observaciones]" rows="3" placeholder="Información adicional sobre el antecedente familiar..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    getTemplateAlergicos(indice) {
        return `
        <div class="card mb-3 border-left-danger" data-index="${indice}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-allergies text-danger mr-2"></i>
              Antecedente Alérgico #${indice + 1}
            </h6>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'alergicos')" title="Duplicar">
                <i class="fas fa-copy"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'alergicos')" title="Eliminar">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-8">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Descripción de la alergia *</label>
                  <input type="text" class="form-control" name="alergicos[${indice}][descripcion]" required placeholder="Alérgeno y tipo de reacción...">
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha de inicio *</label>
                  <input type="date" class="form-control" name="alergicos[${indice}][fecha_inicio]" required max="${new Date().toISOString().split('T')[0]}">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Tratamiento recibido</label>
                  <input type="text" class="form-control" name="alergicos[${indice}][tratamiento_recibido]" placeholder="Medicamentos utilizados...">
                </div>
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Detalle del tratamiento</label>
                  <textarea class="form-control" name="alergicos[${indice}][detalle_tratamiento]" rows="2" placeholder="Descripción del tratamiento..."></textarea>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Complicaciones</label>
                  <textarea class="form-control" name="alergicos[${indice}][complicaciones]" rows="2" placeholder="Complicaciones de la alergia..."></textarea>
                </div>
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha de finalización</label>
                  <input type="date" class="form-control" name="alergicos[${indice}][fecha_finalizacion]">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="activo_aler_${indice}" name="alergicos[${indice}][activo]" value="true" checked>
                    <label class="custom-control-label" for="activo_aler_${indice}">¿Está activo?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="alergicos[${indice}][observaciones]" rows="2" placeholder="Observaciones adicionales..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    getTemplateTraumaticos(indice) {
        return `
        <div class="card mb-3 border-left-warning" data-index="${indice}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-band-aid text-warning mr-2"></i>
              Antecedente Traumático #${indice + 1}
            </h6>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'traumaticos')" title="Duplicar">
                <i class="fas fa-copy"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'traumaticos')" title="Eliminar">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-8">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Descripción del trauma *</label>
                  <input type="text" class="form-control" name="traumaticos[${indice}][descripcion]" required placeholder="Tipo de trauma o lesión...">
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha del trauma *</label>
                  <input type="date" class="form-control" name="traumaticos[${indice}][fecha_inicio]" required max="${new Date().toISOString().split('T')[0]}">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Tratamiento recibido</label>
                  <input type="text" class="form-control" name="traumaticos[${indice}][tratamiento_recibido]" placeholder="Tratamiento inmediato...">
                </div>
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Detalle del tratamiento</label>
                  <textarea class="form-control" name="traumaticos[${indice}][detalle_tratamiento]" rows="2" placeholder="Descripción detallada del tratamiento..."></textarea>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Complicaciones</label>
                  <textarea class="form-control" name="traumaticos[${indice}][complicaciones]" rows="2" placeholder="Complicaciones del trauma..."></textarea>
                </div>
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha de finalización</label>
                  <input type="date" class="form-control" name="traumaticos[${indice}][fecha_finalizacion]">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="activo_traum_${indice}" name="traumaticos[${indice}][activo]" value="true" checked>
                    <label class="custom-control-label" for="activo_traum_${indice}">¿Está activo?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="traumaticos[${indice}][observaciones]" rows="2" placeholder="Observaciones adicionales..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    getTemplateGineco() {
        return `
        <div class="card border-left-info">
          <div class="card-header">
            <h6 class="mb-0">
              <i class="fas fa-venus text-info mr-2"></i>
              Antecedentes Gineco-Obstétricos
            </h6>
            <small class="text-muted">Registro único por paciente</small>
          </div>
          <div class="card-body">
            <!-- Menarquia -->
            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" id="tiene_menarquia" name="gineco[tiene_menarquia]" value="true">
                    <label class="custom-control-label" for="tiene_menarquia">¿Ha tenido menarquia?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group" id="div-edad-menarquia" style="display: none;">
                  <label class="form-control-label font-weight-bold">Edad de menarquia</label>
                  <input type="number" class="form-control" name="gineco[edad_menarquia]" min="8" max="20" placeholder="Años">
                </div>
              </div>
            </div>

            <!-- Menopausia -->
            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" id="tiene_menopausia" name="gineco[tiene_menopausia]" value="true">
                    <label class="custom-control-label" for="tiene_menopausia">¿Ha tenido menopausia?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group" id="div-edad-menopausia" style="display: none;">
                  <label class="form-control-label font-weight-bold">Edad de menopausia</label>
                  <input type="number" class="form-control" name="gineco[edad_menopausia]" min="35" max="65" placeholder="Años">
                </div>
              </div>
            </div>

            <!-- Historia obstétrica -->
            <div class="row">
              <div class="col-md-12">
                <h6 class="text-success mb-3">
                  <i class="fas fa-baby mr-2"></i>Historia Obstétrica
                </h6>
              </div>
            </div>
            <div class="row">
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Gravidez (G)</label>
                  <input type="number" class="form-control" name="gineco[gravidez]" value="0" min="0" max="20">
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Abortos (A)</label>
                  <input type="number" class="form-control" name="gineco[abortos]" value="0" min="0" max="20">
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Hijos Vivos (HV)</label>
                  <input type="number" class="form-control" name="gineco[hijos_vivos]" value="0" min="0" max="20">
                </div>
              </div>
            </div>

            <!-- Planificación familiar -->
            <div class="row">
              <div class="col-md-12">
                <h6 class="text-primary mb-3">
                  <i class="fas fa-shield-alt mr-2"></i>Planificación Familiar
                </h6>
              </div>
            </div>
            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" id="usa_planificacion" name="gineco[usa_metodo_planificacion]" value="true">
                    <label class="custom-control-label" for="usa_planificacion">¿Usa método de planificación?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group" id="div-metodo-planificacion" style="display: none;">
                  <label class="form-control-label font-weight-bold">Método de planificación</label>
                  <select class="form-control" name="gineco[metodo_detalle]">
                    <option value="">Seleccione...</option>
                    <option value="pastillas_anticonceptivas">Pastillas anticonceptivas</option>
                    <option value="inyectable">Inyectable</option>
                    <option value="diu">DIU</option>
                    <option value="implante">Implante</option>
                    <option value="condon">Condón</option>
                    <option value="diafragma">Diafragma</option>
                    <option value="esterilizacion">Esterilización</option>
                    <option value="natural">Método natural</option>
                    <option value="otro">Otro</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="row" id="detalles-planificacion" style="display: none;">
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Dosis</label>
                  <input type="text" class="form-control" name="gineco[dosis_planificacion]" placeholder="Dosis del método...">
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Adherencia</label>
                  <select class="form-control" name="gineco[adherencia_planificacion]">
                    <option value="">Seleccione...</option>
                    <option value="excelente">Excelente</option>
                    <option value="buena">Buena</option>
                    <option value="regular">Regular</option>
                    <option value="mala">Mala</option>
                  </select>
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Tolerancia</label>
                  <select class="form-control" name="gineco[tolerancia_planificacion]">
                    <option value="">Seleccione...</option>
                    <option value="excelente">Excelente</option>
                    <option value="buena">Buena</option>
                    <option value="regular">Regular</option>
                    <option value="mala">Mala</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-12">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="gineco[observaciones]" rows="3" placeholder="Observaciones adicionales sobre antecedentes gineco-obstétricos..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }
    getTemplateEpidemiologicos(indice) {
        return `
        <div class="card mb-3 border-left-info" data-index="${indice}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-virus text-info mr-2"></i>
              Antecedente Epidemiológico #${indice + 1}
            </h6>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'epidemiologicos')" title="Duplicar">
                <i class="fas fa-copy"></i>
              </button>
              <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'epidemiologicos')" title="Eliminar">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-8">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Tipo de antecedente epidemiológico *</label>
                  <input type="text" class="form-control" name="epidemiologicos[${indice}][tipo_antecedente]" required placeholder="Enfermedad infecciosa o epidemiológica...">
                </div>
              </div>
              <div class="col-md-4">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Fecha de inicio *</label>
                  <input type="date" class="form-control" name="epidemiologicos[${indice}][fecha_inicio]" required max="${new Date().toISOString().split('T')[0]}">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="complicaciones_epi_${indice}" name="epidemiologicos[${indice}][complicaciones_asociadas]" value="true">
                    <label class="custom-control-label" for="complicaciones_epi_${indice}">¿Complicaciones asociadas?</label>
                  </div>
                </div>
                <div class="form-group complicaciones-details" id="complicaciones-epi-details-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Detallar complicaciones</label>
                  <textarea class="form-control" name="epidemiologicos[${indice}][detallar_complicaciones]" rows="2" placeholder="Descripción de las complicaciones..."></textarea>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Tratamiento (tipo y posología)</label>
                  <textarea class="form-control" name="epidemiologicos[${indice}][tratamiento_detalle]" rows="2" placeholder="Detalle del tratamiento recibido..."></textarea>
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <div class="custom-control custom-switch">
                    <input type="checkbox" class="custom-control-input" 
                           id="activo_epi_${indice}" name="epidemiologicos[${indice}][activo_actualmente]" value="true" checked>
                    <label class="custom-control-label" for="activo_epi_${indice}">¿Activo actualmente?</label>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group fecha-finalizacion" id="fecha-epi-finalizacion-${indice}" style="display: none;">
                  <label class="form-control-label font-weight-bold">Fecha de finalización</label>
                  <input type="date" class="form-control" name="epidemiologicos[${indice}][fecha_finalizacion]">
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-12">
                <div class="form-group">
                  <label class="form-control-label font-weight-bold">Observaciones</label>
                  <textarea class="form-control" name="epidemiologicos[${indice}][observaciones]" rows="2" placeholder="Observaciones adicionales..."></textarea>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }
    // Agregar estos métodos a la clase AntecedentesEditor

    getTemplateETS(indice) {
        return `
    <div class="card mb-3 border-left-danger" data-index="${indice}">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h6 class="mb-0">
          <i class="fas fa-shield-virus text-danger mr-2"></i>
          Enfermedad de Transmisión Sexual #${indice + 1}
        </h6>
        <div class="btn-group btn-group-sm">
          <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'ets')" title="Duplicar">
            <i class="fas fa-copy"></i>
          </button>
          <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'ets')" title="Eliminar">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      <div class="card-body">
        <div class="row">
          <div class="col-md-8">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Tipo de ETS *</label>
              <select class="form-control" name="ets[${indice}][tipo_ets]" required>
                <option value="">Seleccione una enfermedad...</option>
                <option value="sifilis">Sífilis</option>
                <option value="gonorrea">Gonorrea</option>
                <option value="clamidia">Clamidia</option>
                <option value="herpes_genital">Herpes Genital</option>
                <option value="vih">VIH/SIDA</option>
                <option value="hepatitis_b">Hepatitis B</option>
                <option value="hepatitis_c">Hepatitis C</option>
                <option value="vph">VPH (Virus del Papiloma Humano)</option>
                <option value="tricomoniasis">Tricomoniasis</option>
                <option value="candidiasis">Candidiasis recurrente</option>
                <option value="molluscum">Molluscum Contagiosum</option>
                <option value="otra_ets">Otra ETS</option>
              </select>
            </div>
          </div>
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Fecha diagnóstico *</label>
              <input type="date" class="form-control" name="ets[${indice}][fecha_diagnostico]" required max="${new Date().toISOString().split('T')[0]}">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <div class="custom-control custom-switch">
                <input type="checkbox" class="custom-control-input" 
                       id="tratamiento_ets_${indice}" name="ets[${indice}][tratamiento_recibido]" value="true">
                <label class="custom-control-label" for="tratamiento_ets_${indice}">¿Ha recibido tratamiento médico?</label>
              </div>
            </div>
            <div class="form-group tratamiento-details" id="tratamiento-ets-details-${indice}" style="display: none;">
              <label class="form-control-label font-weight-bold">Detalle del tratamiento</label>
              <textarea class="form-control" name="ets[${indice}][detalle_tratamiento]" rows="2" placeholder="Medicamentos utilizados y duración..."></textarea>
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group">
              <div class="custom-control custom-switch">
                <input type="checkbox" class="custom-control-input" 
                       id="complicaciones_ets_${indice}" name="ets[${indice}][complicaciones]" value="true">
                <label class="custom-control-label" for="complicaciones_ets_${indice}">¿Presentó complicaciones?</label>
              </div>
            </div>
            <div class="form-group complicaciones-details" id="complicaciones-ets-details-${indice}" style="display: none;">
              <label class="form-control-label font-weight-bold">Detalle complicaciones</label>
              <textarea class="form-control" name="ets[${indice}][detalle_complicaciones]" rows="2" placeholder="Complicaciones o secuelas presentadas..."></textarea>
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <div class="custom-control custom-switch">
                <input type="checkbox" class="custom-control-input" 
                       id="curado_ets_${indice}" name="ets[${indice}][curado]" value="true">
                <label class="custom-control-label" for="curado_ets_${indice}">¿Se considera curado completamente?</label>
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group fecha-curacion" id="fecha-ets-curacion-${indice}" style="display: none;">
              <label class="form-control-label font-weight-bold">Fecha curación confirmada</label>
              <input type="date" class="form-control" name="ets[${indice}][fecha_curacion]">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-12">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Observaciones médicas</label>
              <textarea class="form-control" name="ets[${indice}][observaciones]" rows="2" placeholder="Notas adicionales sobre diagnóstico y evolución..."></textarea>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
    }

    getTemplateHospitalizaciones(indice) {
        return `
    <div class="card mb-3 border-left-warning" data-index="${indice}">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h6 class="mb-0">
          <i class="fas fa-hospital text-warning mr-2"></i>
          Hospitalización #${indice + 1}
        </h6>
        <div class="btn-group btn-group-sm">
          <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'hospitalizaciones')" title="Duplicar">
            <i class="fas fa-copy"></i>
          </button>
          <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'hospitalizaciones')" title="Eliminar">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      <div class="card-body">
        <div class="row">
          <div class="col-md-8">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Motivo hospitalización *</label>
              <input type="text" class="form-control" name="hospitalizaciones[${indice}][motivo_hospitalizacion]" required placeholder="Diagnóstico o razón del ingreso hospitalario...">
            </div>
          </div>
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Centro hospitalario *</label>
              <input type="text" class="form-control" name="hospitalizaciones[${indice}][institucion]" required placeholder="Nombre del hospital o clínica...">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Fecha ingreso *</label>
              <input type="date" class="form-control" name="hospitalizaciones[${indice}][fecha_ingreso]" required max="${new Date().toISOString().split('T')[0]}">
            </div>
          </div>
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Fecha egreso</label>
              <input type="date" class="form-control" name="hospitalizaciones[${indice}][fecha_egreso]" max="${new Date().toISOString().split('T')[0]}">
            </div>
          </div>
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Días hospitalizado</label>
              <input type="number" class="form-control" name="hospitalizaciones[${indice}][dias_hospitalizacion]" min="1" placeholder="Duración en días">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <div class="custom-control custom-switch">
                <input type="checkbox" class="custom-control-input" 
                       id="complicaciones_hosp_${indice}" name="hospitalizaciones[${indice}][complicaciones_durante]" value="true">
                <label class="custom-control-label" for="complicaciones_hosp_${indice}">¿Complicaciones durante estancia?</label>
              </div>
            </div>
            <div class="form-group complicaciones-details" id="complicaciones-hosp-details-${indice}" style="display: none;">
              <label class="form-control-label font-weight-bold">Detalle complicaciones</label>
              <textarea class="form-control" name="hospitalizaciones[${indice}][detalle_complicaciones]" rows="2" placeholder="Eventos adversos durante hospitalización..."></textarea>
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group">
              <div class="custom-control custom-switch">
                <input type="checkbox" class="custom-control-input" 
                       id="secuelas_hosp_${indice}" name="hospitalizaciones[${indice}][secuelas]" value="true">
                <label class="custom-control-label" for="secuelas_hosp_${indice}">¿Permanecen secuelas?</label>
              </div>
            </div>
            <div class="form-group secuelas-details" id="secuelas-hosp-details-${indice}" style="display: none;">
              <label class="form-control-label font-weight-bold">Detalle secuelas</label>
              <textarea class="form-control" name="hospitalizaciones[${indice}][detalle_secuelas]" rows="2" placeholder="Secuelas o limitaciones persistentes..."></textarea>
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-12">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Observaciones adicionales</label>
              <textarea class="form-control" name="hospitalizaciones[${indice}][observaciones]" rows="2" placeholder="Información relevante sobre la hospitalización..."></textarea>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
    }

    getTemplateInmunizaciones(indice) {
        return `
    <div class="card mb-3 border-left-success" data-index="${indice}">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h6 class="mb-0">
          <i class="fas fa-syringe text-success mr-2"></i>
          Vacuna/Inmunización #${indice + 1}
        </h6>
        <div class="btn-group btn-group-sm">
          <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'inmunizaciones')" title="Duplicar">
            <i class="fas fa-copy"></i>
          </button>
          <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'inmunizaciones')" title="Eliminar">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      <div class="card-body">
        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Tipo vacuna *</label>
              <select class="form-control" name="inmunizaciones[${indice}][tipo_vacuna]" required>
                <option value="">Seleccione tipo...</option>
                <option value="covid19">COVID-19</option>
                <option value="influenza">Influenza estacional</option>
                <option value="hepatitis_b">Hepatitis B</option>
                <option value="tetanos">Tétanos</option>
                <option value="fiebre_amarilla">Fiebre Amarilla</option>
                <option value="neumococo">Neumococo</option>
                <option value="bcg">BCG (Tuberculosis)</option>
                <option value="dpt">DPT (Difteria-Pertussis-Tétanos)</option>
                <option value="polio">Poliomielitis</option>
                <option value="sarampion">Sarampión</option>
                <option value="rubeola">Rubeola</option>
                <option value="paperas">Paperas</option>
                <option value="varicela">Varicela</option>
                <option value="meningococo">Meningococo</option>
                <option value="rotavirus">Rotavirus</option>
                <option value="haemophilus">Haemophilus influenzae</option>
                <option value="otras_vacunas">Otras vacunas</option>
              </select>
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Nombre comercial vacuna</label>
              <input type="text" class="form-control" name="inmunizaciones[${indice}][nombre_vacuna]" placeholder="Marca o nombre específico...">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Fecha aplicación *</label>
              <input type="date" class="form-control" name="inmunizaciones[${indice}][fecha_aplicacion]" required max="${new Date().toISOString().split('T')[0]}">
            </div>
          </div>
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Dosis número</label>
              <input type="number" class="form-control" name="inmunizaciones[${indice}][dosis_numero]" value="1" min="1" max="10">
            </div>
          </div>
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Lugar aplicación</label>
              <input type="text" class="form-control" name="inmunizaciones[${indice}][lugar_aplicacion]" placeholder="Hospital, centro salud, etc...">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <div class="custom-control custom-switch">
                <input type="checkbox" class="custom-control-input" 
                       id="reacciones_inmun_${indice}" name="inmunizaciones[${indice}][reacciones_adversas]" value="true">
                <label class="custom-control-label" for="reacciones_inmun_${indice}">¿Presentó reacciones adversas?</label>
              </div>
            </div>
            <div class="form-group reacciones-details" id="reacciones-inmun-details-${indice}" style="display: none;">
              <label class="form-control-label font-weight-bold">Detalle reacciones</label>
              <textarea class="form-control" name="inmunizaciones[${indice}][detalle_reacciones]" rows="2" placeholder="Síntomas o reacciones post-vacunación..."></textarea>
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group">
              <div class="custom-control custom-switch">
                <input type="checkbox" class="custom-control-input" 
                       id="refuerzo_inmun_${indice}" name="inmunizaciones[${indice}][refuerzo_programado]" value="true">
                <label class="custom-control-label" for="refuerzo_inmun_${indice}">¿Requiere dosis refuerzo?</label>
              </div>
            </div>
            <div class="form-group refuerzo-details" id="refuerzo-inmun-details-${indice}" style="display: none;">
              <label class="form-control-label font-weight-bold">Fecha próximo refuerzo</label>
              <input type="date" class="form-control" name="inmunizaciones[${indice}][fecha_proximo_refuerzo]" min="${new Date().toISOString().split('T')[0]}">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-12">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Notas adicionales</label>
              <textarea class="form-control" name="inmunizaciones[${indice}][observaciones]" rows="2" placeholder="Observaciones sobre la inmunización..."></textarea>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
    }

    getTemplateTransfusionales(indice) {
        return `
    <div class="card mb-3 border-left-primary" data-index="${indice}">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h6 class="mb-0">
          <i class="fas fa-tint text-primary mr-2"></i>
          Antecedente Transfusional #${indice + 1}
        </h6>
        <div class="btn-group btn-group-sm">
          <button type="button" class="btn btn-outline-info" onclick="window.antecedentesEditor.duplicarItem(this, 'transfusionales')" title="Duplicar">
            <i class="fas fa-copy"></i>
          </button>
          <button type="button" class="btn btn-outline-danger" onclick="window.antecedentesEditor.eliminarItem(this, 'transfusionales')" title="Eliminar">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      <div class="card-body">
        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Componente transfundido *</label>
              <select class="form-control" name="transfusionales[${indice}][tipo_componente]" required>
                <option value="">Seleccione componente...</option>
                <option value="sangre_total">Sangre Total</option>
                <option value="globulos_rojos">Glóbulos Rojos concentrados</option>
                <option value="plaquetas">Concentrado plaquetario</option>
                <option value="plasma">Plasma fresco congelado</option>
                <option value="albumina">Albúmina humana</option>
                <option value="crioprecipitados">Crioprecipitados</option>
                <option value="factor_viii">Factor VIII de coagulación</option>
                <option value="factor_ix">Factor IX de coagulación</option>
                <option value="inmunoglobulinas">Inmunoglobulinas</option>
                <option value="otros_componentes">Otros componentes</option>
              </select>
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Fecha transfusión *</label>
              <input type="date" class="form-control" name="transfusionales[${indice}][fecha_transfusion]" required max="${new Date().toISOString().split('T')[0]}">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-8">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Motivo transfusión *</label>
              <input type="text" class="form-control" name="transfusionales[${indice}][motivo_transfusion]" required placeholder="Indicación médica para la transfusión...">
            </div>
          </div>
          <div class="col-md-4">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Unidades transfundidas</label>
              <input type="number" class="form-control" name="transfusionales[${indice}][cantidad_unidades]" value="1" min="1" max="50">
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Centro médico</label>
              <input type="text" class="form-control" name="transfusionales[${indice}][institucion]" placeholder="Hospital donde se realizó...">
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Grupo sanguíneo confirmado</label>
              <select class="form-control" name="transfusionales[${indice}][grupo_sanguineo_confirmado]">
                <option value="">Seleccione grupo...</option>
                <option value="A+">A positivo (A+)</option>
                <option value="A-">A negativo (A-)</option>
                <option value="B+">B positivo (B+)</option>
                <option value="B-">B negativo (B-)</option>
                <option value="AB+">AB positivo (AB+)</option>
                <option value="AB-">AB negativo (AB-)</option>
                <option value="O+">O positivo (O+)</option>
                <option value="O-">O negativo (O-)</option>
              </select>
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-6">
            <div class="form-group">
              <div class="custom-control custom-switch">
                <input type="checkbox" class="custom-control-input" 
                       id="reacciones_transf_${indice}" name="transfusionales[${indice}][tuvo_reacciones]" value="true">
                <label class="custom-control-label" for="reacciones_transf_${indice}">¿Presentó reacciones adversas?</label>
              </div>
            </div>
            <div class="form-group reacciones-details" id="reacciones-transf-details-${indice}" style="display: none;">
              <label class="form-control-label font-weight-bold">Detalle reacciones</label>
              <textarea class="form-control" name="transfusionales[${indice}][detalle_reacciones]" rows="2" placeholder="Reacciones durante o después de transfusión..."></textarea>
            </div>
          </div>
          <div class="col-md-6">
            <div class="form-group">
              <label class="form-control-label font-weight-bold">Observaciones médicas</label>
              <textarea class="form-control" name="transfusionales[${indice}][observaciones]" rows="3" placeholder="Información adicional sobre la transfusión..."></textarea>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
    }




}