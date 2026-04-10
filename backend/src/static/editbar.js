/* lastClikecAula

saves the DOM element of the last selected cell with a class
*/
let lastClickedAula = null 

function getDropdownConfig(element){
    if(element === '.docentesDropDown'){
        return {
            multipleMode: 'label',
            searchable: true,
            searchNoData: '<li class="cursorHover changeCursor" data-bs-toggle="modal" data-bs-target="#newDocenteModal">Novo Docente</li>'
        }
    }

    return {
        multipleMode: 'label',
        searchable: true,
    }
}

function getDropdownSelectedIds(element){
    return $(element + ' .dropdown-display-label .dropdown-chose-list .dropdown-selected i[data-id]')
        .map(function() { return String($(this).data('id')); })
        .get();
}

function getDropdownSourceOptions(element){
    const select = document.querySelector(element + ' select');
    if(!select) return [];

    return Array.from(select.options).map((option) => ({
        id: String(option.value),
        name: option.textContent.trim(),
        tipo: option.getAttribute('data-tipo') || ''
    }));
}

function setDropdownOptionsKeepingSelection(element, orderedOptions, selectedIds){
    const options = getDropdownConfig(element);
    const dropdown = $(element).dropdown(options).data('dropdown');
    dropdown.update(orderedOptions.map((o) => ({ id: o.id, name: o.name })), true);
    dropdown.reset();

    selectedIds.forEach((id) => {
        dropdown.choose(id, true);
    });
}

function sortOptionsByPriorityIds(options, priorityIds){
    const prioritySet = new Set(priorityIds.map(String));
    const priority = options.filter((o) => prioritySet.has(String(o.id)));
    const rest = options.filter((o) => !prioritySet.has(String(o.id)));
    return [...priority, ...rest];
}

function getSidebarUcDocenteIds(ucId){
    if(!ucId) return [];

    const docenteIds = new Set();
    const ucCells = document.querySelectorAll('td p.uc[id="' + ucId + '"]');

    ucCells.forEach((ucElement) => {
        const cell = ucElement.closest('td');
        if(!cell) return;
        cell.querySelectorAll('p.docente').forEach((docenteElement) => {
            if(docenteElement.id) docenteIds.add(String(docenteElement.id));
        });
    });

    return Array.from(docenteIds);
}

function getSidebarUcSalaIds(ucId){
    if(!ucId) return [];

    const salaIds = new Set();
    const ucCells = document.querySelectorAll('td p.uc[id="' + ucId + '"]');

    ucCells.forEach((ucElement) => {
        const cell = ucElement.closest('td');
        if(!cell) return;
        cell.querySelectorAll('p.sala').forEach((salaElement) => {
            if(salaElement.id) salaIds.add(String(salaElement.id));
        });
    });

    return Array.from(salaIds);
}

function getSalaTypesByIds(salaIds, salaOptions){
    const salaTypeSet = new Set();
    const optionById = new Map(salaOptions.map((o) => [String(o.id), o]));

    salaIds.forEach((id) => {
        const option = optionById.get(String(id));
        if(option && option.tipo) salaTypeSet.add(option.tipo);
    });

    return salaTypeSet;
}

function sortSalasByTipoPriority(salaOptions, priorityTypes){
    if(priorityTypes.size === 0) return salaOptions;

    const matching = salaOptions.filter((o) => priorityTypes.has(o.tipo));
    const rest = salaOptions.filter((o) => !priorityTypes.has(o.tipo));
    return [...matching, ...rest];
}

function applySidebarPriorityForUc(ucId, selectedSalaIds = []){
    if(!ucId) return;

    const docenteOptions = getDropdownSourceOptions('.docentesDropDown');
    const selectedDocentes = getDropdownSelectedIds('.docentesDropDown');
    const ucDocenteIds = getSidebarUcDocenteIds(ucId);
    const orderedDocentes = sortOptionsByPriorityIds(docenteOptions, ucDocenteIds);
    setDropdownOptionsKeepingSelection('.docentesDropDown', orderedDocentes, selectedDocentes);

    const salaOptions = getDropdownSourceOptions('.salasDropDown');
    const selectedSalas = getDropdownSelectedIds('.salasDropDown');
    const ucSalaIds = getSidebarUcSalaIds(ucId);
    const salaIdsForTypePriority = selectedSalaIds.length > 0 ? selectedSalaIds : ucSalaIds;
    const preferredTypes = getSalaTypesByIds(salaIdsForTypePriority, salaOptions);
    const orderedSalas = sortSalasByTipoPriority(salaOptions, preferredTypes);
    setDropdownOptionsKeepingSelection('.salasDropDown', orderedSalas, selectedSalas);
}

/* updateSidebarSelection

selects the options on the sidebar
selects the options corresponding the ids passed as argument
*/
function updateSidebarSelection(idAula, idUc, initTime, timeSpan, day, 
    docentesIdList, salasIdList, turmasIdList){
    const sidebarId = document.querySelector("#editSideBarForm #selectedID")
    sidebarId.value= idAula

    timeSpan = (timeSpan % 2) === 0 ? timeSpan/2*100 : Math.floor(timeSpan/2)*100+30
    let endTime

    if (((initTime + timeSpan) % 100 === 0) || ((initTime + timeSpan) % 100 === 30)){
        endTime = initTime + timeSpan
    }
    else{
        endTime = initTime + timeSpan + 40
    }

    if(idUc !== null) updateSidebarSingle(idUc, "cadeiraEdit")
    if(initTime !== null && initTime>=800 && initTime<=1900) updateSidebarSingle(initTime, "hora-inicio")
    if(initTime!==null && timeSpan!==null && timeSpan>=0
        && endTime>=800 && endTime<=2000) updateSidebarSingle(endTime, "hora-fim")
    if(day!==null) updateSidebarSingle(day, "dia")
    if(docentesIdList!==null && docentesIdList.length>0) updateSidebarMultiple(docentesIdList, '.docentesDropDown')
    if(salasIdList!==null && salasIdList.length>0) updateSidebarMultiple(salasIdList, '.salasDropDown')
    if(turmasIdList!==null && turmasIdList.length>0) updateSidebarMultiple(turmasIdList, '.turmasDropDown')

    if(idUc !== null){
        applySidebarPriorityForUc(String(idUc), (salasIdList || []).map(String));
    }
}

/* updateSidebarSingle

receives and id and an elementId
updates the select on the elementId
with the option with the id passed as argument
*/
function updateSidebarSingle(id, elementId){
    let dropdown = document.getElementById(elementId);
    dropdown.value = id;
}

/* updateSideBarEmpty

updates the sidebar with the time, duration and date of the selected empty cell
CURRENTLY UNUSED
*/
function updateSideBarEmpty(initTime, timeSpan, day){
    const sidebarId = document.querySelector("#editSideBarForm #selectedID")
    sidebarId.value= "-1"

    timeSpan = (timeSpan % 2) === 0 ? timeSpan/2*100 : (timeSpan-1)/2*100+30

    if(initTime !== null && initTime>=800 && initTime<=1900) updateSidebarSingle(initTime, "hora-inicio")
    if(initTime!==null && timeSpan!==null && timeSpan>=0
        && (initTime+timeSpan)>=800 && (initTime+timeSpan)<=2000) updateSidebarSingle(initTime + timeSpan, "hora-fim")
    if(day!==null) updateSidebarSingle(day, "dia")

    updateSidebarMultiple([], '.docentesDropDown')
    updateSidebarMultiple([], '.salasDropDown')
    updateSidebarMultiple([], '.turmasDropDown')

    let cadeiras = document.getElementById("cadeiraEdit");
    cadeiras.selectedIndex=-1
}

/* updateSidebarMultiple

updates the dropdown select element with the corresponding element class
receives a list of ids of options to select on the dropdown select 
*/
function updateSidebarMultiple(ids, element){
    let options = getDropdownConfig(element)

    let dropdown = $(element).dropdown(options).data('dropdown')
    dropdown.reset()

    //select new options
    ids.forEach(element => {
        dropdown.choose(element, true)
    });
}

/* setSidebarUCs

called whenever the displayed schedule is updated
updates the UCs options on the UCs select on the sidebar to represent the present UCs
*/
function setSidebarUCs(ucSet){
    const selectElement = document.getElementById("cadeiraEdit")
    while (selectElement.firstChild) {
        selectElement.removeChild(selectElement.firstChild);
    }

    ucSet.forEach(uc => {
        let option = document.createElement("option")
        option.value = uc.codigo
        option.text = uc.nome
        selectElement.appendChild(option)
    });
}

/* setSidebarTurmas

called whenever the displayed schedule is updated
updates the Turmas options on the Turmas dropdown select on the sidebar to represent the present Turmas
*/
function setSidebarTurmas(turmasSet){
    const turmasList = Array.from(turmasSet)
    turmasList.sort()

    const turmasDropDownDiv = document.querySelector(".turmasDropDown")
    
    //formatar
    const list = turmasList.map((str) => {
        return { name: str, id: str };
    });
    
    //criar o dropdown select object e mudar as opcoes
    $(".turmasDropDown").dropdown({
        // options here
        multipleMode: 'label',
        searchable: true,
    }).data("dropdown").update(list, true)
}

/* showEditBarOptions

receives a showBool
if true displays the sidebar edit form
if false hides it and displays a "selecione uma aula" message
*/
function showEditBarOptions(showBool){
    const formDiv = document.getElementById("edit-form-div")
    const hiddenDiv = document.getElementById("edit-form-hidden-div")
    if(showBool){
        if(!hiddenDiv.classList.contains("hidden")) hiddenDiv.classList.add("hidden")
        if(formDiv.classList.contains("hidden")) formDiv.classList.remove("hidden")
        return
    }

    hiddenDiv.classList.remove("hidden")
    formDiv.classList.add("hidden")
}

/* event listener

event: ctrl+e

toggles the sidebar modal
*/
$(document).ready(function () {
    const cadeiraEdit = document.getElementById('cadeiraEdit');
    if(cadeiraEdit){
        cadeiraEdit.addEventListener('change', function(){
            applySidebarPriorityForUc(String(this.value));
        });
    }

    document.addEventListener('keydown', function(event) {
        if (event.ctrlKey && event.key === 'e') {
            event.preventDefault(); // Prevent the default browser behavior (e.g., opening the browser's search feature)
            let offcanvas = document.getElementById('offcanvasDarkNavbar');
            let offcanvasInstance = bootstrap.Offcanvas.getInstance(offcanvas);
            if (!offcanvasInstance) {
                new bootstrap.Offcanvas(offcanvas).show(); // Initialize and show the offcanvas sidebar
            } else {
                offcanvasInstance.toggle(); // Toggle the offcanvas sidebar
            }
        }
    })
})

/* selectedCellSelectSideBar

receives the selected element, and whether or not it is an empty cell
if isEmpty, updates the sidebar to display empty options CURRENTLY UNUSED
else gets the top <td> element selected, collects its attributes, selects them in the sidebar
and unhides the sidebar, if needed
*/
function selectedCellSelectSideBar(element, isEmpty){
    //obter o element correto
    while(element.tagName !=="TD"){
        element = element.parentNode
    }
    lastClickedAula = element

    let idUc, initTime, timeSpan, day, idAula
    let docentesIdList=[], salasIdList=[], turmasIdList=[]
    const pList = element.querySelectorAll("p")
    
    //idAula, initTime, timespan, day
    idAula=element.getAttribute("data-aulaid")
    timeSpan = element.hasAttribute("rowspan") ? parseInt(element.getAttribute("rowspan"), 10) : 1

    let timeDayArray = element.id.split("_").slice(-2)
    initTime = parseInt(timeDayArray[1], 10)
    day = switchDaytoNumber(timeDayArray[0])
    
    //uc, docentes e salas
    pList.forEach(p_element => {
        switch (p_element.classList[0]) {
            case "uc":
                idUc = p_element.id
                break;
            case "docente":
                docentesIdList.push(p_element.id)
                break
            case "sala":
                salasIdList.push(p_element.id)
                break;
            default:
                break;
        }
    });

    //turmas
    let turmasSet = new Set()
    let turmasDiv = element.querySelectorAll("div")
    turmasDiv.forEach(div => {
        turmasSet.add(div.id.split("_")[1])
    });
    turmasIdList = Array.from(turmasSet)
    if(isEmpty){
        updateSideBarEmpty(initTime, timeSpan, day)
        return
    }
    updateSidebarSelection(idAula, idUc, initTime, timeSpan, day, docentesIdList, salasIdList, turmasIdList)
}

/*switchDaytoNumber 

auxiliary function
receives a weekday string and returns the corresponding week day number
*/
function switchDaytoNumber(numberString){
    switch (numberString) {
        case "segunda":
            return "0"
        case "terça":
            return "1"
        case "quarta":
            return "2"
        case "quinta":
            return "3"
        case "sexta":
            return "4"
        case "sábado":
            return "5"
        default:
            return null
    }
}

/* writeConflicts

receives a list of strings containing conflicts
removes currently displayed conflicts
shows the conflicts passed as argument 
*/
function writeConflicts(arrayOfConflicts){
    $('#conflictsList').empty()
    $.each(arrayOfConflicts, function(key, value){
        $('#conflictsList').append('<li>' + value + '</li>')
    })
}

/* editSideBarForm submit

event: sidebar submit button pressed

retrieves the selected options
in the case of turmas, also retrieves the other turmas with the same aula not displayed in the sidebar
sends a Post Ajax Request that makes the necessary changes and returns a list of conflicts
retrieves the update curso JSON, displays it and displays the received conflicts
*/ 
$(document).ready(function () {
    $('#editSideBarForm').submit(function () {
        event.preventDefault()

        //get project id
        const url = window.location.pathname;
        const id = url.split('/').pop();

        //get data from sidebar
        var turmasIds = [];
        var docentesIds = [];
        var salasIds = [];
    
        $('.turmasDropDown .dropdown-display-label .dropdown-chose-list .dropdown-selected i[data-id]').each(function() {
            let dataId = $(this).data('id');
            turmasIds.push(dataId);
        });
        
        $('.docentesDropDown .dropdown-display-label .dropdown-chose-list .dropdown-selected i[data-id]').each(function() {
            let dataId = $(this).data('id');
            docentesIds.push(dataId);
        });

        $('.salasDropDown .dropdown-display-label .dropdown-chose-list .dropdown-selected i[data-id]').each(function() {
            let dataId = $(this).data('id');
            salasIds.push(dataId);
        });

        if(lastClickedAula.getAttribute('data-teorica') == 0){
            const aulaId = lastClickedAula.getAttribute('data-aulaid')
            let aulas = Array.from(document.querySelectorAll('[data-aulaid="' + aulaId + '"]'))
            const index = aulas.indexOf(lastClickedAula)
            if(index !== -1){
                aulas.splice(index, 1)
            }

            aulas.forEach(element => {
                const colspan = parseInt(element.getAttribute('colspan') )
                const childDivs = Array.from(element.getElementsByTagName('div')).slice(0, colspan);

                childDivs.forEach(child =>{
                    const id = child.id
                    turmasIds.push(id.split('_')[1])
                })
            });
        }

        var formData = {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
            projId:id,
            aulaId: $('input[name="selectedID"]').val(),
            cadeiraId: $('select[name="cadeiraEdit"]').val(),
            horaInicio: $('select[name="hora-inicio"]').val(),
            horaFim: $('select[name="hora-fim"]').val(),
            dia: $('select[name="dia"]').val(),
            turmasIds: turmasIds,
            docentesIds: docentesIds,
            salasIds: salasIds
        };

        // create an AJAX call
        $.ajax({
            data: JSON.stringify(formData),
            type: $(this).attr('method'), // GET or POST
            url: "/editturnos/"+id+"/makechanges",

            headers:{
                'X-CSRFToken': formData.csrfmiddlewaretoken
            },

            // on success
            success: function (response) {
                //mudar no horario
                handleCursoBtn(0, true, ano, true);

                //conflitos
                const conflicts = response.conflicts
                writeConflicts(conflicts)
            },
            // on error
            error: function (response, status, error) {
                console.log(response.responseText)
            }
        });
        
        return false;
    });
})

/* newDocenteForm submit

event: submit button in new Docente modal clicked
retrieves the inputed attributes
sends them in a Post Ajax request that verifies if the new id is taken
if it is taken, a error message is diplayed under the id input
otherwise the docente is created and selected in the dropdown
*/
$(document).ready(function () {
    $('#newDocenteForm').submit(function () {
        event.preventDefault()

        const errorContainer = $('#error-container-docente')
        
        //remove any error message
        errorContainer.empty()

        const url = window.location.pathname;
        const id = url.split('/').pop();

        idDocente = $('input[name="idDocente"]').val()
        nomeDocente = $('input[name="nomeDocente"]').val()
        siglaDocente = $('input[name="siglaDocente"]').val()

        $.ajax({
            data: $(this).serialize(), // get the form data
            type: $(this).attr('method'), // GET or POST
            url: "/editturnos/"+id+"/createDocente/",

            // on success
            success: function (response) {
                $('#newDocenteModal').modal('hide')
                let dropdown =  $(".docentesDropDown").dropdown({
                    multipleMode: 'label',
                    searchable: true,
                    searchNoData: '<li class="cursorHover changeCursor" data-bs-toggle="modal" data-bs-target="#newDocenteModal">Novo Docente</li>'
                }).data("dropdown")
                
                
                //reselecionar docentes
                var docentesIds = []
                $('.docentesDropDown .dropdown-display-label .dropdown-chose-list .dropdown-selected i[data-id]').each(function() {
                    let dataId = $(this).data('id');
                    docentesIds.push(dataId);
                });

                idDocente = response.idDocente
                nomeDocente = response.nomeDocente
                siglaDocente = response.siglaDocente

                dropdown.update([{ name: siglaDocente+' - '+nomeDocente, id: idDocente}], false)
                dropdown.reset()
                docentesIds.forEach(element => {
                    dropdown.choose(element, true)
                });
                //selecionar o novo docente
                dropdown.choose(idDocente, true)
            },
            // on error
            error: function (response, status, error) {
                if(response.status == 409){
                    const errorMessage = $('<p class="text-danger">Número Mecanográfico Inválido ou Repetido!</p>')
                    errorContainer.append(errorMessage)
                }else{
                    console.log(response.responseText)
                    alert(response.responseText)
                }
            }
        });
        return false;
    });
})
