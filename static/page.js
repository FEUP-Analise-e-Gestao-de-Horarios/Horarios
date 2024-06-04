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

function handleCursoBtn(anoNum, updateDom = false, selectedAno = null, handleDist = false) {
    let cursoNome = cursoBtn.value;

    if (cursoNome == "Curso") {
        cursoNome = "L.EIC";
    }

    if (anoNum === 0) {
        anoNum = ano;
    }

    // Make the asynchronous request
    $.ajax({
        url: '/table/',  // Update with your actual URL
        type: 'GET',
        data: { 'curso': cursoNome, 'projId': projId, 'anoNum': anoNum },
        success: function (data) {
            document.querySelector(".main_vista_container").innerHTML = data.schedulehtml;
            updateColspan();

            const cursoJson = data.curso_json;
            curso = JSON.parse(cursoJson);
            ano = curso.anos[0].ano;
            semana = 'Semanas';

            updateAnoButton(data, selectedAno);
            updateTurnosButton();
            updateTurmasButton(data);
            updateSemanasButton(data);

            dataLoadBool = true;

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

function handleDistributionBtn(show) {
    const table = document.querySelector(".secondary_vista_container");

    if (!show && table.style.display === "") {
        table.setAttribute("style", "display: none;");
    }
    else if (show && table.style.display === "none") {
        return;
    }
    else {
        var ucs = curso.ucs;
        var ucsCodigosList = [];
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

function updateAnoButton(data, anoSelected) {
    anoBtn.innerHTML = "<option selected>Ano</option>";
    for (let i = 1; i <= data.numAnos; i++) {
        const new_option = document.createElement("option");
        new_option.value = i;
        new_option.innerHTML = i;
        if (i == anoSelected) new_option.selected = 'selected'
        anoBtn.appendChild(new_option);
    }
}

function updateTurnosButton() {
    turnosBtn.innerHTML = "<option selected>Turnos</option>";
    const turmasPorTurno = curso.anos[0].turmasPorTurno;
    for (let turno in turmasPorTurno) {
        const new_option = document.createElement("option");
        const turno_text = turno.replace(/\(.*?\)/g, '');
        new_option.value = turno_text;
        new_option.innerHTML = turno_text;
        turnosBtn.appendChild(new_option);
    }
}

function updateTurmasButton(data) {
    turmasBtn.innerHTML = "<option selected>Turma</option>";
    for (let i = 0; i < data.numeroTurmas; i++) {
        const new_option = document.createElement("option");
        new_option.value = data.turmasAno[i];
        new_option.innerHTML = data.turmasAno[i];
        turmasBtn.appendChild(new_option);
    }
}

function updateSemanasButton(data) {
    semanasBtn.innerHTML = "<option selected>Semanas</option>";
    for (let i = 0; i < data.semanasAno.length; i++) {
        const semanaPair = data.semanasAno[i];
        const semanaPairString = semanaPair[0] + ' - ' + semanaPair[1];
        const new_option = document.createElement("option");
        new_option.value = semanaPairString;
        new_option.innerHTML = semanaPairString;
        semanasBtn.appendChild(new_option);
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