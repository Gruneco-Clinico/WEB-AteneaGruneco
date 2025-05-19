document.addEventListener('DOMContentLoaded', function() {
    // Estado para controlar qué formularios están abiertos
    const formulariosAbiertos = new Set();
    
    // Manejar clicks en los elementos del dropdown
    document.querySelectorAll('.dropdown-item[data-form]').forEach(item => {
        item.addEventListener('click', async function(event) {
            event.preventDefault(); // Prevenir la navegación

            const formType = this.dataset.form;

            if (formulariosAbiertos.has(formType)) {
                // Si el formulario está abierto, lo cerramos
                document.getElementById(`container-${formType}`).remove();
                formulariosAbiertos.delete(formType);
            } else {
                // Si el formulario está cerrado, lo abrimos
                try {
                    const response = await fetch(`templates/sleepexams/${formType}/`);
                    console.log("Response status:", response.status);
                    if (response.ok) {
                        const formHtml = await response.text();
                        const container = document.createElement('div');
                        container.id = `container-${formType}`;
                        container.className = 'row mb-4';
                        container.innerHTML = formHtml;
                        document.getElementById('formularios-dinamicos').appendChild(container);
                        formulariosAbiertos.add(formType);
                        
                        // Inicializar el nuevo formulario
                        initializeForm(formType);
                    }
                } catch (error) {
                    console.error('Error cargando el formulario:', error);
                    Swal.fire({
                        title: 'Error',
                        text: 'No se pudo cargar el formulario',
                        icon: 'error'
                    });
                }
            }
        });
    });
    
    // Función para inicializar un formulario específico
    function initializeForm(formType) {
        const form = document.querySelector(`#form-${formType}`);
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            
            try {
                const response = await fetch(`/api/formularios/${formType}/guardar/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    Swal.fire({
                        title: '¡Éxito!',
                        text: 'Datos guardados correctamente',
                        icon: 'success'
                    });
                } else {
                    throw new Error('Error al guardar');
                }
            } catch (error) {
                Swal.fire({
                    title: 'Error',
                    text: 'Error al guardar los datos',
                    icon: 'error'
                });
            }
        });
    }
});
