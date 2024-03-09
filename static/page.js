var cursosLista = JSON.parse(document.currentScript.getAttribute('data-cursos')); //FORMATO -> [nome_do_curso]
var projId = document.currentScript.getAttribute('data-proj-id');

var cursoBtn = document.getElementById("cursoBtn");
var curso, ano, semana, ucsDistribuicao;
let dataLoadBool = false;
//var numeroTurnos, numeroTurmas, turmasPorTurno, turmasAno, semanasAno;

for(let i=0; i<cursosLista.length; i++) {
    var new_option = document.createElement("option");
    new_option.value = cursosLista[i];
    new_option.innerHTML = cursosLista[i];
    cursoBtn.appendChild(new_option);
}

function handleCursoBtn(anoNum, updateDom=false, selectedAno=null, handleDist = false) {
    var cursoBtn = document.getElementById("cursoBtn");
    var cursoNome = cursoBtn.value;

    if(cursoNome == "Curso") {
        //cursoNome = cursoBtn.options[1].value;
        cursoNome = "L.EIC";
    }

    if(anoNum === 0) {
        anoNum = ano;
    }
    //console.log("ANO NUM: ", anoNum);
    // Make the asynchronous request
    $.ajax({
        url: '/table/',  // Update with your actual URL
        type: 'GET',
        data: {'curso': cursoNome, 'projId': projId, 'anoNum': anoNum},
        success: function(data) {
            document.querySelector(".main_vista_container").innerHTML = data.schedulehtml;
            updateColspan();

            var cursoJson = data.curso_json;
            curso = JSON.parse(cursoJson);
            ano = curso.anos[0].ano;
            semana = 'Semanas';

            var anoBtn = document.getElementById("anoBtn");
            anoBtn.innerHTML = "<option selected>Ano</option>";
            for(let i=1; i<=data.numAnos; i++){
                var new_option = document.createElement("option");
                new_option.value = i;
                new_option.innerHTML = i;
                if(i == selectedAno) new_option.selected = 'selected'
                anoBtn.appendChild(new_option);
            }

            var turnosBtn = document.getElementById("turnosBtn");
            turnosBtn.innerHTML = "<option selected>Turnos</option>";
            for(let i=1; i<=data.numeroTurnos; i++){
                var new_option = document.createElement("option");
                new_option.value = i;
                new_option.innerHTML = i;
                turnosBtn.appendChild(new_option);
            }

            var turmasBtn = document.getElementById("turmasBtn");
            turmasBtn.innerHTML = "<option selected>Turma</option>";
            for(let i=0; i<data.numeroTurmas; i++){
                var new_option = document.createElement("option");
                new_option.value = data.turmasAno[i];
                new_option.innerHTML = data.turmasAno[i];
                turmasBtn.appendChild(new_option);
            }

            var semanasBtn = document.getElementById("semanasBtn");
            semanasBtn.innerHTML = "<option selected>Semanas</option>";
            for(let i=0; i<data.semanasAno.length; i++) {
                var semanaPair = data.semanasAno[i];
                var semanaPairString = semanaPair[0] + ' - ' + semanaPair[1];
                var new_option = document.createElement("option");
                new_option.value = semanaPairString;
                new_option.innerHTML = semanaPairString;
                semanasBtn.appendChild(new_option);
            }
            dataLoadBool = true;

            if(updateDom){
                updateColspan();
                //console.log('colspan updated')
                fillUcs(ano);
                //console.log('fillUcs')
                fillDocentes(ano);
                //console.log('fillDocentes')
                fillSalas(ano);
                //console.log('fillSalas')
                handleDistributionBtn(handleDist);
                //console.log('handleDistributionBtn')
            }
        },
        error: function(xhr, textStatus, error) {
            //console.log(textStatus)
            dataLoadBool = false;
        }
    });
}

/*document.addEventListener("DOMContentLoaded", function() {
    handleCursoBtn(1);
});*/

document.getElementById("cursoBtn").addEventListener("change", function() {
    //console.log("curso change")
    handleCursoBtn(1);
});

document.getElementById("anoBtn").addEventListener("change", function() {
    if(this.value==='Ano')
        ano = this.options[1].value;
    else
        ano = this.value;
    handleCursoBtn(ano, dataLoadBool, ano);
});         

document.getElementById("turnosBtn").addEventListener("change", function() {
    //console.log("turnos change")
    const allTurnos = this.options;

    if(this.value === 'Turnos') {
        mergeTurnos();
    }
    else {
        unmergeTurnos();
    }

    for (let i = 0; i < allTurnos.length; i++) {
        const turno_num = allTurnos[i].value;
        if(this.value === 'Turnos') {
            turno = ".turno" + turno_num;
            const turnoCol = document.querySelectorAll(turno);
            turnoCol.forEach(function(cell) {
                cell.style.display = '';
            });
        }
        else if(turno_num === this.value) {
            turno = ".turno" + turno_num;
            const turnoCol = document.querySelectorAll(turno);
            turnoCol.forEach(function(cell) {
                cell.style.display = '';
            });
        }
        else if(turno_num !== this.value) {
            turno = ".turno" + turno_num;
            const turnoCol = document.querySelectorAll(turno);
            turnoCol.forEach(function(cell) {
                cell.style.display = 'none';
            });
        }
    }

    updateColspan();
});

document.getElementById("turmasBtn").addEventListener("change", function() {
    //console.log("turmas change")
    const allTurmas = this.options;
    const turmasLista = curso.anos[0].turmas;

    if(this.value === 'Turma') {
        mergeCells();
    }
    else {
        unmergeCells(turmasLista);
    }
    
    for(let i=0; i<allTurmas.length; i++) {
        const turma_nome = allTurmas[i].value;

        if(turma_nome === this.value || this.value === 'Turma') {
            turma = "#turma_" + turma_nome;
            const turmaCol = document.querySelectorAll(turma);
            turmaCol.forEach(cell => cell.style.display = '');

            substring = "turma_" + turma_nome;
            const elements = document.querySelectorAll("[id*=" + substring + "]");
            elements.forEach(cell => cell.style.display = '');
            continue;
        }

        if(turma_nome !== this.value) {
            turma = "#turma_" + turma_nome;
            const turmaCol = document.querySelectorAll(turma);
            turmaCol.forEach(cell => cell.style.display = 'none');

            substring = "turma_" + turma_nome;
            const elements = document.querySelectorAll("[id*=" + substring + "]");
            elements.forEach(cell => cell.style.display = 'none');
        }
    }

    //updateColspanMergedCells();        

    updateColspan();
});

document.getElementById("semanasBtn").addEventListener("change", function() {
    //console.log("semanas change")
    semana = this.value;

    // Make the asynchronous request
    $.ajax({
        url: '/table/',  // Update with your actual URL
        type: 'GET',
        data: {'curso': curso.nome, 'projId': projId},
        success: function(data) {
            document.querySelector(".main_vista_container").innerHTML = data.schedulehtml;

            updateColspan();
            fillUcs(ano);
            fillDocentes(ano);
            fillSalas(ano);
        },
        error: function(xhr, textStatus, error) {
            // Handle any errors
        }
    });
});

function handleDistributionBtn(show) {
    const table = document.querySelector(".secondary_vista_container");

    if(!show && table.style.display === "") {
        //console.log("Display vazio");
        table.setAttribute("style", "display: none;");
    }
    else if(show && table.style.display === "none"){
        return;
    }
    else {
        //console.log("Display none");
        var ucs = curso.ucs;
        var ucsCodigosList = [];
        for(let i=0; i<ucs.length; i++) {
            if(ucs[i].anos.includes(ano)) {
                ucsCodigosList.push(ucs[i].codigo);
            }
        }

        //console.log("Ucs codigos: ", ucsCodigosList);

        $.ajax({
            url: '/distribuicao/',
            type: 'GET',
            data: {'projId': projId, 'ucsLista': ucsCodigosList.join(',')},
            success: function(data) {
                table.innerHTML = data.distribuicaohtml;
                ucsDistribuicao = data.ucsDistribuicao;
                //console.log("Distribuição on success: ", data.ucsDistribuicao);
                fillTable();
                table.setAttribute("style", "display: ;");
            }
        })
    }
}

document.getElementById("showDistributionBtn").addEventListener("click", function() {
    handleDistributionBtn(false);
});

$(document).ready(function () {
    document.addEventListener('keydown', function(event) {
        if (event.ctrlKey && event.key === 'd') {
            event.preventDefault(); // Prevent the default browser behavior (e.g., opening the browser's search feature)
            handleDistributionBtn(false);
        }
    })
})