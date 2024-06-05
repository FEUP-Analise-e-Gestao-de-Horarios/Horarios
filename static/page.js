const cursosLista = JSON.parse(document.currentScript.getAttribute('data-cursos')); //FORMATO -> [nome_do_curso]
const projId = document.currentScript.getAttribute('data-proj-id');

const cursoBtn = document.getElementById("cursoBtn");
const anoBtn = document.getElementById("anoBtn");
const turnosBtn = document.getElementById("turnosBtn");
const turmasBtn = document.getElementById("turmasBtn");
const semanasBtn = document.getElementById("semanasBtn");
const distributionBtn = document.getElementById("showDistributionBtn");

let curso, ano, semana, ucsDistribuicao;
let dataLoadBool = false;

/**
 * Lida com o evento de clique no botão de seleção de curso
 * 
 * @param {number} anoNum - O ano escolhido
 * @param {boolean} [updateDom=false] - Flag que indica se o DOM deve ser atualizado
 * @param {string} [selectedAno=null] - O ano atualmente selecionado.
 * @param {boolean} [handleDist=false] - Flag que indica se deve ser atualizada a tabela de distribuição.
 * @returns {null} Não retorna qualquer valor
 */
function handleCursoBtn(anoNum, updateDom = false, selectedAno = null, handleDist = false) {
    let cursoNome = cursoBtn.value;

    if (cursoNome == "Curso") {
        cursoNome = "L.EIC";
    }

    if (anoNum === 0) {
        anoNum = ano;
    }

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
            ano = curso.anos[0].ano;
            semana = 'Semanas';

            // Atualiza o conteúdo de todos os botões de seleção
            updateAnoButton(data.numAnos, selectedAno);
            updateTurnosButton(curso.anos[0].turmasPorTurno);
            console.log(curso.anos[0].turmasPorTurno);
            updateTurmasButton(data.turmasAno);
            updateSemanasButton(data.semanasAno);

            dataLoadBool = true;

            // Caso seja necessário, atualiza o conteúdo da página
            if (updateDom) {
                updateColspan();
                fillUcs(ano);
                fillDocentes(ano);
                fillSalas(ano);
                handleDistributionBtn(handleDist);
            }
        },
        error: function (xhr, textStatus, error) {
            dataLoadBool = false;
        }
    });
}

/**
 * Lida com o evento de clique no botão de distribuição.
 * @param {boolean} show - Flag que indica se a tabela de distribuição deve ser mostrada.
 * @returns {null} Não retorna qualquer valor.
 */
function handleDistributionBtn(show) {
    const table = document.querySelector(".secondary_vista_container");

    if (!show && table.style.display === "") {
        table.setAttribute("style", "display: none;");
    }
    else if (show && table.style.display === "none") {
        return;
    }
    else {
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
        })
    }
}

/**
 * Obtém as turmas de um dado turno, usando um endpoint do backend.
 * 
 * @param {string} turno - O turno para o qual obter as turmas.
 * @returns {Promise<Array>} - Um array de turmas.
 */
function fetchTurmasForTurno(turno) {
    return $.ajax({
        url: '/getTurmasPorTurnoCursoAno',
        type: 'GET',
        data: { 'turno': turno },
    });
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
    createAndAppendOptions(turnosBtn, turnos, "Turno");
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
        if (i - 1 === selectedOption) new_option.selected = 'selected';
        selectElement.appendChild(new_option);
    }
}

cursoBtn.addEventListener("change", function () {
    handleCursoBtn(1);
});

anoBtn.addEventListener("change", function () {
    if (this.value === 'Ano')
        ano = this.options[1].value;
    else
        ano = this.value;
    handleCursoBtn(ano, dataLoadBool, ano);
});

turnosBtn.addEventListener("change", function () {
    const allTurnos = this.options;
    const selectedTurno = this.value;

    // if (selectedTurno === 'Turnos') {
    //     displayAllTurmas();
    // } else {
    //     fetchTurmasForTurno(selectedTurno)
    //         .then(displayTurmasForTurno)
    //         .catch(error => {
    //             console.error('Error fetching turmas:', error);
    //         });
    // }

    if (this.value === 'Turnos') {
        mergeTurnos();
    }
    else {
        unmergeTurnos();
    }

    for (let i = 0; i < allTurnos.length; i++) {
        const turno_num = allTurnos[i].value;
        if (this.value === 'Turnos') {
            turno = ".turno" + turno_num;
            const turnoCol = document.querySelectorAll(turno);
            turnoCol.forEach(function (cell) {
                cell.style.display = '';
            });
        }
        else if (turno_num === this.value) {
            turno = ".turno" + turno_num;
            const turnoCol = document.querySelectorAll(turno);
            turnoCol.forEach(function (cell) {
                cell.style.display = '';
            });
        }
        else if (turno_num !== this.value) {
            turno = ".turno" + turno_num;
            const turnoCol = document.querySelectorAll(turno);
            turnoCol.forEach(function (cell) {
                cell.style.display = 'none';
            });
        }
    }
    updateColspan();
});

turmasBtn.addEventListener("change", function () {
    const allTurmas = this.options;
    const turmasLista = curso.anos[0].turmas;

    if (this.value === 'Turma') {
        mergeCells();
    }
    else {
        unmergeCells(turmasLista);
    }

    for (let i = 0; i < allTurmas.length; i++) {
        const turma_nome = allTurmas[i].value;

        if (turma_nome === this.value || this.value === 'Turma') {
            turma = "#turma_" + turma_nome;
            const turmaCol = document.querySelectorAll(turma);
            turmaCol.forEach(cell => cell.style.display = '');

            substring = "turma_" + turma_nome;
            const elements = document.querySelectorAll("[id*=" + substring + "]");
            elements.forEach(cell => cell.style.display = '');
            continue;
        }

        if (turma_nome !== this.value) {
            turma = "#turma_" + turma_nome;
            const turmaCol = document.querySelectorAll(turma);
            turmaCol.forEach(cell => cell.style.display = 'none');

            substring = "turma_" + turma_nome;
            const elements = document.querySelectorAll("[id*=" + substring + "]");
            elements.forEach(cell => cell.style.display = 'none');
        }
    }
    updateColspan();
});

semanasBtn.addEventListener("change", function () {
    semana = this.value;

    // Make the asynchronous request
    $.ajax({
        url: '/table/',
        type: 'GET',
        data: { 'curso': curso.nome, 'projId': projId },
        success: function (data) {
            document.querySelector(".main_vista_container").innerHTML = data.schedulehtml;

            updateColspan();
            fillUcs(ano);
            fillDocentes(ano);
            fillSalas(ano);
        },
        error: function (xhr, textStatus, error) {
            console.log(textStatus);
        }
    });
});

distributionBtn.addEventListener("click", function () {
    handleDistributionBtn(false);
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