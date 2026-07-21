# C-14 — Paginación/navegación del listado (scroll horizontal)

- **Épica:** C — UX / Exportación
- **Tipo:** enhancement / UX
- **Prioridad:** Baja
- **Componentes:** Listados (pacientes/formularios)

## Contexto (reunión)
En los listados con barra de navegación horizontal, el usuario debe desplazarse hasta el final para
encontrar la barra/scroll. Los jóvenes investigadores lo reportaron. Workaround actual: `Shift` +
scroll del mouse mueve horizontalmente. La solución propuesta es **paginar** el listado (mostrar un
número limitado de registros por página en vez de todo) para evitar el scroll infinito.

## Comportamiento esperado
1. Paginar el listado (N registros por página) con controles de paginación.
2. Alternativamente/además, fijar la barra de desplazamiento visible sin tener que llegar al final.

## Referencias técnicas
- Vistas de listado: `apps/home/views/patients.py` (listado de pacientes).
- Plantillas de listado en `apps/templates/info_paciente/` / `home/`.

## Notas
- Prioridad baja: hay workaround (`Shift`+scroll) y no bloquea el uso.

## Criterios de aceptación
- [x] El listado se pagina y no requiere scroll hasta el final para navegar.
- [x] Controles de paginación funcionales (siguiente/anterior/número de página).
