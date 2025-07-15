const cursosLista = JSON.parse(document.currentScript.getAttribute('data-cursos')); //FORMATO -> [nome_do_curso]
const projId = document.currentScript.getAttribute('data-proj-id');

const cursoBtn = document.getElementById("cursoBtn");
const anoBtn = document.getElementById("anoBtn");
const turnosBtn = document.getElementById("turnosBtn");
const turmasBtn = document.getElementById("turmasBtn");
const semanasBtn = document.getElementById("semanasBtn");
const distributionBtn = document.getElementById("showDistributionBtn");

let curso, ano, semana, ucsDistribuicao, turmasPorTurno;
let dataLoadBool = false;
let distributionActive = true;

function handleCursoBtn(cursoNome) {
    if (cursoNome === "Curso") {
        updateAnoButton(0, "Ano");
        return;
    }

    $.ajax({
        url: '/emptytable/',
        type: 'GET',
        data: { 'curso': cursoNome, 'projId': projId },
        success: function (data) {
            updateAnoButton(data.numAnos, "Ano");
        },
        error: function (xhr, textStatus, error) {
            console.error("Error fetching anos:", error);
        }
    })
}

/**
 * Lida com o evento de clique no botão de seleção de curso
 * 
 * @param {number} anoNum - O ano escolhido
 * @param {string} [selectedAno] - O ano atualmente selecionado.
 * @param {boolean} [handleDist=false] - Flag que indica se deve ser atualizada a tabela de distribuição.
 * @returns {null} Não retorna qualquer valor
 */
function handleAnoBtn(anoNum, selectedAno, handleDist = false) {
    return new Promise((resolve, reject) => {
        let cursoNome = cursoBtn.value;

        // Realiza o pedido assíncrono
        $.ajax({
            url: '/table/',
            type: 'GET',
            data: { 'curso': cursoNome, 'projId': projId, 'anoNum': anoNum },
            success: function (data) {
                document.querySelector(".main_vista_container").innerHTML = data.schedulehtml;
                updateColspan();

                const cursoJson = data.curso_json;
                curso = JSON.parse(cursoJson);
                turmasPorTurno = data.turmasPorTurno;
                ano = curso.anos[0].ano;
                semana = 'Semanas';

                // Atualiza o conteúdo de todos os botões de seleção
                updateAnoButton(data.numAnos, selectedAno);
                updateTurnosButton(turmasPorTurno);
                updateTurmasButton(data.turmasAno);
                updateSemanasButton(data.semanasAno);

                dataLoadBool = true;

                // Atualiza o conteúdo da página                
                fillUcs(ano);
                fillDocentes(ano);
                fillSalas(ano);
                enablePopovers();

                resolve(data);
            },
            error: function (xhr, textStatus, error) {
                dataLoadBool = false;
                reject(error);
            }
        });
    });
}

/**
 * Lida com o evento de clique no botão de distribuição.
 * @returns {null} Não retorna qualquer valor.
 */
function handleDistributionBtn() {
    const table = document.querySelector(".secondary_vista_container");

    if (distributionActive) {
        if (table.style.display !== "none") return;

        let ucs = curso.ucs;
        let ucsCodigosList = [];
        for (let i = 0; i < ucs.length; i++) {
            if (ucs[i].anos.includes(ano)) {
                ucsCodigosList.push(ucs[i].codigo);
            }
        }

        $.ajax({
            url: '/distribuicao/',
            type: 'GET',
            data: { 'projId': projId, 'ucsLista': ucsCodigosList.join(',') },
            success: function (data) {
                table.innerHTML = data.distribuicaohtml;
                ucsDistribuicao = data.ucsDistribuicao;
                fillTable();
                table.setAttribute("style", "display: ;");
            }
        });
    } else {
        table.style.display = "none";
    }
    distributionActive = !distributionActive;
}

/**
 * Atualiza o botão de seleção de ano com os dados fornecidos.
 *
 * @param {number} numAnos - Número de anos.
 * @param {number} anoSelected - Ano atualmente selecionado.
 * @returns {null} Não retorna qualquer valor.
 */
function updateAnoButton(numAnos, anoSelected) {
    const anos = Array.from({ length: numAnos }, (_, i) => i + 1);
    createAndAppendOptions(anoBtn, anos, "Ano", anoSelected);
}

/**
 * Atualiza o botão dos turnos com base nas opções possíveis.
 *
 * @param {Object} turmasPorTurno - Objeto que contém as turmas agrupadas por turno.
 * @returns {null} Não retorna qualquer valor.
 */
function updateTurnosButton(turmasPorTurno) {
    const turnos = Object.keys(turmasPorTurno);
    createAndAppendOptions(turnosBtn, turnos, "Turnos");
}

/**
 * Atualiza o botão das turmas com base nas opções possíveis
 * 
 * @param {string[]} turmas - Turmas existentes.
 * @return {null} Não retorna qualquer valor.
 */
function updateTurmasButton(turmas) {
    createAndAppendOptions(turmasBtn, turmas, "Turma");
}

/**
 * Atualiza o botão das semanas com base nas opções possíveis
 * 
 * @param {string[][]} semanas - Semanas organizadas em períodos, definidos por semana inicial e final.
 * @return {null} Não retorna qualquer valor.
 */
function updateSemanasButton(semanas) {
    const semanasStrings = semanas.map(semanaPair => semanaPair[0] + ' - ' + semanaPair[1]);
    createAndAppendOptions(semanasBtn, semanasStrings, "Semanas");
}

/**
 * Função auxiliar para criar e adicionar 'options' a um dado elemento HTML.
 * 
 * @param {HTMLElement} selectElement - O elemento que vai receber as novas opções.
 * @param {Array} options - Array de opções a adicionar. 
 * @param {any} selectedOption - A opção a ser selecionada.
 * @returns {null} Não retorna qualquer valor.
 */
function createAndAppendOptions(selectElement, options, genericOptionText, selectedOption = null) {
    selectElement.innerHTML = "<option selected>" + genericOptionText + "</option>";
    for (let i = 0; i < options.length; i++) {
        const new_option = document.createElement("option");
        new_option.value = options[i];
        new_option.innerHTML = options[i];
        if (options[i] == selectedOption) new_option.selected = 'selected';
        selectElement.appendChild(new_option);
    }
}

// ------------------------------------------------------------------------------------------------
// Event listeners
// ------------------------------------------------------------------------------------------------

cursoBtn.addEventListener("change", function () {
    let cursoNome = cursoBtn.value;

    let anoNum = anoBtn.value;
    if (anoNum === "Ano") anoNum = 1;

    handleCursoBtn(cursoNome, anoNum);
});

anoBtn.addEventListener("change", function () {
    ano = this.value;
    handleAnoBtn(ano, ano).then(updateDayDivisions);
});

turnosBtn.addEventListener("change", function () {
    const selectedTurno = this.value;

    if (selectedTurno === 'Turnos') {
        displayAllAulas();
        updateColspan();
    } else {
        displayTurmasForTurno(turmasPorTurno[selectedTurno]);
        updateColspan();
    }
    updateDayDivisions();
});

turmasBtn.addEventListener("change", function () {
    if (this.value === 'Turma') {
        displayAllAulas();
        updateColspan();
    } else {
        displayTurma(this.value);
        updateColspan();
    }
    updateDayDivisions();
});

semanasBtn.addEventListener("change", function () {
    semana = this.value;
    let anoNum;
    if (anoBtn.value === 'Ano') {
        anoNum = 1;
    } else {
        anoNum = anoBtn.value;
    }

    $.ajax({
        url: '/table/',
        type: 'GET',
        data: { 'curso': curso.nome, 'projId': projId, 'anoNum': anoNum, 'semanas': semana },
        success: function (data) {
            document.querySelector(".main_vista_container").innerHTML = data.schedulehtml;

            curso = JSON.parse(data.curso_json);
            ano = curso.anos[0].ano;
            updateColspan();
            fillUcs(ano);
            fillDocentes(ano);
            fillSalas(ano);
            enablePopovers();
        },
        error: function (xhr, textStatus, error) {
            console.log(textStatus);
        }
    });
});

distributionBtn.addEventListener("click", function () {
    handleDistributionBtn();
});

document.addEventListener('DOMContentLoaded', function () {
    const exportBtn = document.getElementById('exportBtn');
    exportBtn.addEventListener('click', function () {
        window.location.href = "/export/" + projId;
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const conflictsBtn = document.getElementById('conflictsBtn');
    conflictsBtn.addEventListener('click', function() {
        window.location.href = "/conflicts/" + projId;
    });
});

for (let i = 0; i < cursosLista.length; i++) {
    const new_option = document.createElement("option");
    new_option.value = cursosLista[i];
    new_option.innerHTML = cursosLista[i];
    cursoBtn.appendChild(new_option);
}

$(document).ready(function () {
    document.addEventListener('keydown', function (event) {
        if (event.ctrlKey && event.key === 'd') {
            event.preventDefault(); // Prevent the default browser behavior (e.g., opening the browser's search feature)
            handleDistributionBtn(false);
        }
    })
})