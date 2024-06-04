/**
 * Preenche o campo da sala nas células do horário
 * 
 * @param {number} ano - O ano para o qual devem ser geradas as salas
 * @returns {null} - Não retorna qualquer valor
 */
function fillSalas(ano) {
    const allSalas = curso.salas;

    for (let i = 0; i < allSalas.length; i++) {
        var sala = allSalas[i];
        var aulas = sala.aulas;

        for (let j = 0; j < aulas.length; j++) {
            var aula = aulas[j];

            if (semana !== "Semanas") {
                var semanaInicial = semana.split(" - ")[0];
                var semanaFinal = semana.split(" - ")[1];

                if (aula.semanaInicial !== semanaInicial || aula.semanaFinal !== semanaFinal) {
                    continue;
                }
            }

            var turmas = aula.turmas; //FORMATO -> {ano: [codigoTurma]}

            if (!(ano in turmas)) { //Caso não tenha turmas do ano em que a tabela está
                continue;
            }

            turmas = turmas[ano];
            var dia = aula.diaSemana.toLowerCase();
            var hora = aula.horaInicial;

            for (let k = 0; k < turmas.length; k++) {
                var turma = turmas[k];

                var idString = "turma_" + turma + "_" + dia + "_" + hora;

                var cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); //célula a que pertence a aula
                if (cell == null) {
                    continue;
                }

                var p_element = document.createElement("p");
                p_element.classList.add("sala");
                p_element.id = sala.numero;
                p_element.innerHTML = sala.numero;
                p_element.style.display = "inline-block";
                var br = document.createElement("br");
                cell.appendChild(br);
                cell.appendChild(p_element);
                cell.setAttribute("rowspan", aula.duracao);
            }
        }
    }
}

function fillUcs(ano) {
    const allUCs = curso.ucs;
    const ucAnoSet = new Set();
    const turmasSet = new Set();
    let ucAnoBool = false;

    for (let i = 0; i < allUCs.length; i++) {
        let uc = allUCs[i];
        let aulas = uc.aulas; //FORMATO -> [Aula(id, horaInicial, duracao, diaSemana, isTeorica)]
        ucAnoBool = false;

        for (let j = 0; j < aulas.length; j++) {
            let aula = aulas[j];

            if (semana !== "Semanas") {
                let semanaInicial = semana.split(" - ")[0];
                let semanaFinal = semana.split(" - ")[1];

                if (aula.semanaInicial !== semanaInicial || aula.semanaFinal !== semanaFinal) {
                    continue;
                }
            }

            let turmas = aula.turmas; //FORMATO -> {ano: [codigoTurma]}

            if (!(ano in turmas)) { //Caso não tenha turmas do ano em que a tabela está
                continue;
            }
            ucAnoBool = true;

            turmas = turmas[ano];

            const dia = aula.diaSemana.toLowerCase();
            const hora = aula.horaInicial;

            for (let k = 0; k < turmas.length; k++) {
                let turma = turmas[k];
                turmasSet.add(turma);

                let idString = "turma_" + turma + "_" + dia + "_" + hora;   //id da célula a que pertence a aula

                let cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); //célula a que pertence a aula
                if (cell == null) {
                    continue;
                }

                cell.setAttribute("data-aulaID", aula.id);

                let deleteHorizontal = 0;
                let deleteVertical = aula.duracao - 1;
                if (aula.isTeorica) {
                    deleteHorizontal = turmas.length - 1;
                } else {
                    let turmasLista = curso.anos[0].turmas;
                    let turmaIndex = turmasLista.indexOf(turma);
                    for (let t = 0; t + turmaIndex < turmasLista.length; t++) {
                        if (turmas[k + t] == turmasLista[turmaIndex + t]) {
                            deleteHorizontal += 1;
                        }
                        else {
                            break;
                        }
                    }
                    deleteHorizontal -= 1;
                    k = k + deleteHorizontal;
                }

                deleteCells(cell, deleteHorizontal, deleteVertical);

                const sigla = uc.sigla.slice(0, uc.sigla.indexOf("("));
                const p_element = document.createElement("p");
                p_element.classList.add("uc");
                p_element.id = uc.codigo;
                p_element.innerHTML = sigla;
                p_element.style.display = "inline-block";
                cell.appendChild(p_element);
                cell.setAttribute("rowspan", aula.duracao);
                cell.setAttribute("data-semanas", aula.semanaInicial + ' - ' + aula.semanaFinal);

                if (aula.isTeorica) {
                    cell.setAttribute("colspan", turmas.length);
                    cell.setAttribute("data-originalcolspan", turmas.length);
                    cell.setAttribute("style", "border: 2px solid black;");
                    cell.setAttribute("style", "background-color: " + window.colorDictionary[ucAnoSet.size][1]);
                    cell.setAttribute("data-teorica", 1)
                    break;
                }
                else {
                    cell.setAttribute("colspan", deleteHorizontal + 1);
                    cell.setAttribute("data-originalcolspan", deleteHorizontal + 1);
                    cell.setAttribute("style", "border: 2px solid black;");
                    cell.setAttribute("style", "background-color: " + window.colorDictionary[ucAnoSet.size][0]);
                    cell.setAttribute("data-teorica", 0);
                }
            }
        }
        if (ucAnoBool) ucAnoSet.add(uc);
        //if(uc.codigo == 'M.EIC007') break;
    }
    setSidebarUCs(ucAnoSet);
    setSidebarTurmas(turmasSet);
}

function createCells(cell, cellsRight, cellsBottom, startingVal) {
    /*
    console.log("Create cells for: ", cell);
    console.log("    Cells right: ", cellsRight);
    console.log("    Cells bottom: ", cellsBottom);*/
    var table = document.getElementById("table_vistas");
    const turmasLista = curso.anos[0].turmas;

    var rowspan = cell.getAttribute('rowspan') ? parseInt(cell.getAttribute('rowspan')) : 1;

    var rowIndex = cell.parentNode.rowIndex;
    var cellClass = cell.classList[0];
    var cellId = cell.id;
    var cellTurma = cellId.split("_")[1];
    var turmaIndex = turmasLista.indexOf(cellTurma);

    for (var i = 0; i < cellsBottom; i++) {
        var row = table.rows[rowIndex + i];
        for (var j = startingVal; j <= cellsRight; j++) {
            if ((startingVal == 0 && i == 0 && j == 0) || (startingVal == 1 && i < rowspan && j == 1))
                continue;
            var index = (turmaIndex + j - startingVal + turmasLista.length) % turmasLista.length;
            var newCellTurma = turmasLista[index];
            var newCellId = cellId.split("_")[0] + '_' + newCellTurma + '_' + cellId.split("_")[2] + '_' + cellId.split("_")[3];

            var newCellRowIndex = findHorizontalPosition(row.cells, newCellId);
            var newCell = row.insertCell(newCellRowIndex);
            newCell.classList.add(cellClass);
            newCell.setAttribute('id', newCellId);
            //console.log("Cell created: ", newCell);
        }
        var hora = parseInt(cellId.split('_')[3]);

        secondDigit = (hora / 10) % 10;
        if (secondDigit == 3) {
            hora += 70;
        }
        else {
            hora += 30;
        }

        cellId = cellId.split('_')[0] + "_" + cellId.split('_')[1] + "_" + cellId.split('_')[2] + "_" + hora; //id da célula seguinte pertencente à mesma aula
    }

}

function findHorizontalPosition(row, cellToInsertID) {
    var day = cellToInsertID.split('_')[2];
    var turma = cellToInsertID.split('_')[1];
    var rowIndex = 0;

    const turmasLista = curso.anos[0].turmas;
    const dias = ["segunda", "terça", "quarta", "quinta", "sexta"];

    for (var i = 0; i < dias.length; i++) {
        var turmasDia = 0;
        for (var j = 0; j < row.length; j++) {
            var cellId = row[j].id;
            var cellDay = cellId.split('_')[2];
            var cellTurma = cellId.split('_')[1];
            var cellTurmaIndex = turmasLista.indexOf(cellTurma);
            var turmaIndex = turmasLista.indexOf(turma);

            if (dias[i] === day && cellDay === day && cellTurmaIndex >= turmaIndex) {
                break;
            }

            if (cellDay === dias[i]) {
                turmasDia++;
            }
        }

        rowIndex += turmasDia;

        if (dias[i] === day)
            break;
    }
    return rowIndex + 1;
}

function deleteCells(cell, cellsRight, cellsBottom) {
    /*
    console.log("Delete cells for: ", cell);
    console.log("    Cells right: ", cellsRight);
    console.log("    Cells bottom: ", cellsBottom);*/
    var table = document.getElementById("table_vistas");
    var originalCell = cell;

    var rowIndex = cell.parentNode.rowIndex;
    var cellIndex = cell.cellIndex;
    var idCell = cell.id;

    var firstRow = table.rows[1];
    var top = 0;

    for (var i = 0; i <= cellsBottom; i++) {
        var row = table.rows[rowIndex + i];
        count = cellsRight;
        while (count >= 0) {
            var cellToDelete = row.cells[cellIndex + count];
            var cellToGetHeight = row.cells[0];
            var cellToGetWidth = firstRow.cells[cellIndex + count];
            var idToDelete = cellToDelete.id;
            var div = document.createElement("div");
            div.classList.add("inside_tds");
            div.id = idToDelete;

            var rectHeight = cellToGetHeight.getBoundingClientRect();
            var rectWidth = cellToGetWidth.getBoundingClientRect();

            var rect = cellToDelete.getBoundingClientRect();
            var width = rectWidth.width;
            var height = rectHeight.height

            if (count == cellsRight) {
                left = cellsRight * width;
            }
            else {
                left -= width;
            }

            div.setAttribute("style", "left: " + left + "px; top: " + top + "px; height: " + height + "px; width: " + width + "px;");
            originalCell.style.position = "relative"; // Add this line
            originalCell.appendChild(div);

            if (i == 0 && count == 0) {
                break;
            }

            row.deleteCell(cellIndex + count);
            count--;
        }

        top += height;

        var hora = parseInt(idCell.split('_')[3]);

        secondDigit = (hora / 10) % 10;
        if (secondDigit == 3) {
            hora += 70;
        }
        else {
            hora += 30;
        }

        if (i != cellsBottom) {
            idCell = idCell.split('_')[0] + "_" + idCell.split('_')[1] + "_" + idCell.split('_')[2] + "_" + hora; //id da célula seguinte pertencente à mesma aula
            //console.log("Next cell Id: ", idCell);
            cell = document.querySelector("td[id='" + idCell + "']");
            cellIndex = cell.cellIndex;
        }
    }
}

/**
 * Preenche o campo do docente nas células do horário
 *
 * @param {string} ano - O ano para o qual as células devem ser preenchidas
 * @returns {null} - Não retorna qualquer valor
 */
function fillDocentes(ano) {
    const allDocentes = curso.anos[0].docentes;
    for (let i = 0; i < allDocentes.length; i++) {
        let docente = allDocentes[i];
        let aulas = docente.aulas;

        for (let j = 0; j < aulas.length; j++) {
            let aula = aulas[j];

            if (semana !== "Semanas") {
                var semanaInicial = semana.split(" - ")[0];
                var semanaFinal = semana.split(" - ")[1];

                if (aula.semanaInicial !== semanaInicial || aula.semanaFinal !== semanaFinal) {
                    continue;
                }
            }

            let turmas = aula.turmas; //FORMATO -> {ano: [codigoTurma]}

            if (!(ano in turmas)) { //Caso não tenha turmas do ano em que a tabela está
                continue;
            }

            turmas = turmas[ano];
            let dia = aula.diaSemana.toLowerCase();
            let hora = aula.horaInicial;

            for (let k = 0; k < turmas.length; k++) {
                let turma = turmas[k];

                let idString = "turma_" + turma + "_" + dia + "_" + hora;

                let cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); //célula a que pertence a aula
                if (cell == null) {
                    continue;
                }

                const p_element = document.createElement("p");
                p_element.classList.add("docente");
                p_element.id = docente.numMecanografico;
                p_element.innerHTML = docente.abreviacao;

                const br = document.createElement("br");
                p_element.style.display = "inline-block";
                cell.appendChild(br);
                cell.appendChild(p_element);
                cell.setAttribute("rowspan", aula.duracao);
            }
        }
    }
}

function mergeTurnos() {
    const cells = $("#table_vistas").find("td:not(:first-child):has(p)").toArray();
    cells.forEach(function (cell) {
        const colspan = parseInt(cell.getAttribute('colspan'));
        const originalColspan = parseInt(cell.getAttribute('data-originalcolspan'));

        if (colspan === originalColspan || !colspan)
            return;

        const aulaId = cell.getAttribute('data-aulaid');
        const nextSibling = document.querySelector("tbody td:not(:first-child).turno2[data-aulaid='" + aulaId + "']");
        if (nextSibling) {
            nextSibling.remove();
        }
        cell.setAttribute('colspan', originalColspan);
    })
}

function unmergeTurnos() {
    const cells = $('#table_vistas').find('td:not(:first-child):has(p)').toArray();
    //console.log(cells)
    const turmasporturno = curso.anos[0].turmasPorTurno;
    const numTurmasTurno = turmasporturno[1].length;
    const turmasLista = curso.anos[0].turmas;

    cells.forEach(function (cell) {
        var colspan = parseInt(cell.getAttribute('colspan'));
        if (colspan <= numTurmasTurno || !colspan)
            return;

        var cellId = cell.id;
        cell.setAttribute('colspan', numTurmasTurno);

        var newCell = cell.cloneNode(true);
        var newCellTurma = turmasLista[numTurmasTurno];
        var newCellId = cellId.split('_')[0] + '_' + newCellTurma + '_' + cellId.split("_")[2] + '_' + cellId.split("_")[3];
        newCell.setAttribute('id', newCellId);
        newCell.setAttribute('class', 'turno2');
        newCell.setAttribute('colspan', turmasporturno[2].length);

        cell.parentNode.insertBefore(newCell, cell.nextSibling);
    })
}

function mergeCells() {
    const cells = $("#table_vistas").find("td:not(:first-child):has(p)").toArray();


    cells.forEach(function (cell) {
        var colspan = parseInt(cell.getAttribute('colspan'));
        var originalColspan = parseInt(cell.getAttribute('data-originalcolspan'));

        if (originalColspan === colspan || !originalColspan) {
            return;
        }

        var aulaId = cell.getAttribute('data-aulaid');

        var nextSiblings = document.querySelectorAll("tbody td:not(:first-child)[data-aulaid='" + aulaId + "']");

        for (var i = 1; i < nextSiblings.length; i++) {
            nextSiblings[i].remove();
        }

        cell.setAttribute('colspan', originalColspan);
    })
}

function unmergeCells(turmasLista) {
    const cells = $("#table_vistas").find("td:not(:first-child):has(p)").toArray();

    const turmasporturno = curso.anos[0].turmasPorTurno;

    cells.forEach(function (cell) {
        var colspan = parseInt(cell.getAttribute('colspan'));

        // If the cell is already unmerged or has no colspan, skip it
        if (colspan === 1 || !colspan) {
            return;
        }

        var cellId = cell.id;
        var cellTurma = cellId.split("_")[1];
        var turmaIndex = turmasLista.indexOf(cellTurma);

        for (var i = 1; i < colspan; i++) {
            var newCell = cell.cloneNode(true);
            var newCellTurma = turmasLista[turmaIndex + i];
            var newCellTurno = "turno";

            //Encontrar o turno a que pertence a célula
            for (const [key, arr] of Object.entries(turmasporturno)) {
                if (arr.includes(newCellTurma)) {
                    newCellTurno += key.toString();
                    break;
                }
            }

            var newCellId = cellId.split("_")[0] + '_' + newCellTurma + '_' + cellId.split("_")[2] + '_' + cellId.split("_")[3];
            newCell.setAttribute('id', newCellId);
            newCell.setAttribute('class', newCellTurno);
            newCell.setAttribute('colspan', 1);

            cell.parentNode.insertBefore(newCell, cell.nextSibling);
        }

        cell.setAttribute('colspan', '1');
    });
}

function updateColspan() {
    const table = document.getElementById("table_vistas");
    const headerRow = table.querySelector("thead tr");

    const children = [];
    const columns = table.querySelector("tbody tr:first-child");

    //Coloca em children apenas os elementos que estão visíveis
    for (let i = 0; i < columns.children.length; i++) {
        const child = columns.children[i];
        if (child.style.display === '') {
            children.push(child);
        }
    }

    const numColumns = children.length - 1; //nº de colunas visíveis
    const colspanValue = Math.floor(numColumns / 6);

    headerRow.querySelectorAll("th").forEach((th, index) => {
        if (index === 0) {
            th.setAttribute("colspan", 1);
        } else {
            th.setAttribute("colspan", colspanValue);
        }
    });
}

$(document).on('click', 'td:not(:first-child)', function (event) {
    const td = this;
    const targetElement = event.target;
    var turma = td.id.split('_')[1];

    // Check if the target element is the td itself or a descendant of the td
    if (targetElement === td || $.contains(td, targetElement)) {
        // Unselect any selected p element
        const selectedP = $('td:not(:first-child) p.selected');
        if (selectedP.length) {
            showEditBarOptions(false);
            selectedP.removeClass('selected');
            displayBlocosVermelhosGlobal(selectedP.attr('class'), selectedP.attr('id'), false);
        }

        //Caso se tente selecionar uma célula que já estava selecionada
        if ($(td).hasClass('selected')) {
            showEditBarOptions(false)
            $(td).removeClass('selected');
            displayBlocosVermelhosTurma(turma, false);
            return;
        }

        const prevSelectedCell = $('td:not(:first-child).selected');
        // Caso já exista uma célula selecionada, então é preciso trocá-las
        if (prevSelectedCell.length === 1) {
            // td / prevSelectedCell
            var prevCell = document.querySelector("td:not(:first-child).selected");
            var idCellBefore = $(prevCell).attr('id');
            displayBlocosVermelhosTurma(idCellBefore.split('_')[1], false);
            displayBlocosVermelhosTurma(turma, false);

            try {
                if (canSwap(prevCell, td)) {
                    swapFullCells(prevCell, td);
                    if (prevCell.querySelector("p") !== null) {
                        submitToDatabase(prevCell);
                    }
                    if (td.querySelector("p") !== null) {
                        submitToDatabase(td);
                    }
                    handleDistributionBtn(true);
                }
            } catch (error) {
                console.error("An error occurred in canSwap or swapFullCells:", error);
            }
            showEditBarOptions(false);
        }

        // remove class from all other td
        document.querySelectorAll("td:not(:first-child)").forEach(td => {
            showEditBarOptions(false);
        });

        //Unselect da primeira célula selecionada
        $('td:not(:first-child)').removeClass('selected');
        var idCellBefore = $('td:not(:first-child)').attr('id');

        if (prevSelectedCell.length == 0) {
            //Select da primeira célula selecionada
            $(td).addClass('selected');
            if ($(td).has('p').length > 0) {
                displayBlocosVermelhosTurma(turma, true);
            }
        }

        if (td.children.length > 0) {
            showEditBarOptions(true);
            selectedCellSelectSideBar(targetElement, false);
        }
        else showEditBarOptions(false);
    }
});

$(document).on('mouseenter', '#table_vistas td:not(:first-child):has(p) p.uc', function (event) {
    // MUDAR UCS
    //console.log("Entered cell");
    const uc = this;
    var siglaUC = uc.textContent;
    for (var i = 0; i < curso.ucs.length; i++) {
        var uc_sigla = curso.ucs[i].sigla;
        var indexOfParenthesis = uc_sigla.indexOf("(");
        if (indexOfParenthesis !== -1) {
            uc_sigla = uc_sigla.substring(0, indexOfParenthesis);
        }
        if (siglaUC == uc_sigla) {
            var name = curso.ucs[i].nome;
            if (!document.getElementById("tooltipcontainer")) {
                tooltipcontainer = document.createElement("div");
                tooltipcontainer.setAttribute("id", "tooltipcontainer");
                tooltipcontainer.style.position = "fixed";
                tooltipcontainer.style.left = Math.max(event.clientX + 10, 0) + "px";
                tooltipcontainer.style.top = Math.max(event.clientY - 25, 0) + "px";
                tooltipcontainer.style.zIndex = 999;


                tooltip = document.createElement("div");
                tooltip.style.position = "fixed";

                tooltip.style.width = "auto";
                tooltip.style.backgroundColor = "black";
                tooltip.style.color = "#fff";
                tooltip.style.padding = "5px";
                tooltip.style.zIndex = "999";
                tooltip.style.fontSize = "13px";
                tooltip.textContent = name;


                tooltipcontainer.appendChild(tooltip);

                tableVistas = document.getElementById("table_vistas").parentNode;
                tableVistas.insertBefore(tooltipcontainer, tableVistas.firstChild);
            }
            //uc.textContent = name;
            //uc.style.whiteSpace = "nowrap"; // Set white-space to nowrap
        }
    }



});

$(document).on('mouseleave', '#table_vistas td:not(:first-child):has(p) p.uc', function (event) {
    // MUDAR UCS
    const td = this;
    var nameUC = td.textContent;

    for (var i = 0; i < curso.ucs.length; i++) {
        var this_name = curso.ucs[i].nome;
        if (nameUC == this_name) {
            var siglaUC = curso.ucs[i].sigla;
            var indexOfParenthesis = siglaUC.indexOf("(");
            if (indexOfParenthesis !== -1) {
                siglaUC = siglaUC.substring(0, indexOfParenthesis);
            }

            td.textContent = siglaUC;
        }
    }
    if (document.getElementById("tooltipcontainer")) {
        document.getElementById("tooltipcontainer").parentNode.removeChild(document.getElementById("tooltipcontainer"));
    }
});

$(document).on('mouseenter', '#table_vistas td:not(:first-child):has(p) p.docente', function (event) {
    // MUDAR UCS
    //console.log("Entered cell");    

    // MUDAR DOCENTES
    var docente = this;
    var siglaDocente = this.textContent;

    for (var i = 0; i < curso.docentes.length; i++) {
        var doc_sigla = curso.docentes[i].abreviacao;
        if (siglaDocente == doc_sigla) {
            if (!document.getElementById("tooltipcontainer")) {
                var name = curso.docentes[i].nome;
                tooltipcontainer = document.createElement("div");
                tooltipcontainer.setAttribute("id", "tooltipcontainer");
                tooltipcontainer.style.position = "fixed";
                tooltipcontainer.style.left = Math.max(event.clientX + 10, 0) + "px";
                tooltipcontainer.style.top = Math.max(event.clientY - 25, 0) + "px";
                tooltipcontainer.style.zIndex = 999;
                tooltipcontainer.style.opacity = 0;
                tooltipcontainer.style.transition = "opacity 1s ease-in";
                tooltipcontainer.style.opacity = 1;


                tooltip = document.createElement("div");
                tooltip.style.position = "fixed";

                tooltip.style.width = "auto";
                tooltip.style.backgroundColor = "black";
                tooltip.style.color = "#fff";
                tooltip.style.padding = "5px";
                tooltip.style.zIndex = "999";
                tooltip.style.fontSize = "13px";
                tooltip.textContent = name;


                tooltipcontainer.appendChild(tooltip);

                tableVistas = document.getElementById("table_vistas").parentNode;
                tableVistas.insertBefore(tooltipcontainer, tableVistas.firstChild);
            }
        }

    }
});

$(document).on('mouseleave', '#table_vistas td:not(:first-child)', function (event) {
    if (document.getElementById("tooltipcontainer")) {
        document.getElementById("tooltipcontainer").parentNode.removeChild(document.getElementById("tooltipcontainer"));
    }
});

$(document).on('mouseleave', '#table_vistas td:not(:first-child):has(p) p.docente', function (event) {
    // MUDAR UCS
    var docente = this;
    var nomeDocente = this.textContent;

    for (var i = 0; i < curso.docentes.length; i++) {
        var nome_doc = curso.docentes[i].nome;
        if (nomeDocente == nome_doc) {
            var sigla = curso.docentes[i].abreviacao;
            docente.textContent = sigla;
            docente.style.whiteSpace = "nowrap"; // Set white-space to nowrap
        }
    }
    if (document.getElementById("tooltipcontainer")) {
        document.getElementById("tooltipcontainer").parentNode.removeChild(document.getElementById("tooltipcontainer"));
    }
});


$(document).on('click', 'td:not(:first-child) p', function (event) {
    event.stopPropagation(); // Prevent click event from propagating to the td element

    const p = this;

    // Unselect any selected td element
    const selectedTD = $('td:not(:first-child).selected');
    if (selectedTD.length) {
        var selectedTDId = selectedTD.attr('id');
        //displayBlocosVermelhosTurma(selectedTDId.split('_')[1]);
        selectedTD.removeClass('selected');
        showEditBarOptions(false);
    }

    if (p.classList.contains('selected')) {
        $(p).removeClass('selected');
        displayBlocosVermelhosGlobal(p.className, p.id, false);
        showEditBarOptions(false);
        return;
    }

    const prevSelectedCell = $('td:not(:first-child) p.selected');
    // Caso já exista uma célula selecionada, então é preciso trocá-las
    if (prevSelectedCell.length === 1) {
        var cellClass = prevSelectedCell[0].classList;
        displayBlocosVermelhosGlobal(cellClass, prevSelectedCell[0].id, false);
        showEditBarOptions(false);

        if (cellClass.contains('sigla') && p.classList.contains('uc')) {
            swapPartialCells(prevSelectedCell[0], p);
            submitToDatabase(prevSelectedCell[0].parentNode);
            submitToDatabase(p.parentNode);
        } else if (cellClass.contains('docente') && p.classList.contains('docente')) {
            swapPartialCells(prevSelectedCell[0], p);
            submitToDatabase(prevSelectedCell[0].parentNode);
            submitToDatabase(p.parentNode);
        } else if (cellClass.contains('sala') && p.classList.contains('sala')) {
            swapPartialCells(prevSelectedCell[0], p);
            submitToDatabase(prevSelectedCell[0].parentNode);
            submitToDatabase(p.parentNode);
        }
    }

    // remove class from all other p
    document.querySelectorAll("td:not(:first-child) p").forEach(p_cell => {
        showEditBarOptions(false);
    });

    $('td:not(:first-child) p').removeClass('selected');

    if (prevSelectedCell.length == 0) {
        // add class to clicked p
        $(p).addClass('selected');
        showEditBarOptions(true);
        displayBlocosVermelhosGlobal(p.className, p.id, true);
    }
});

function submitToDatabase(cell) {
    //get project id
    const url = window.location.pathname;
    const id = url.split('/').pop();

    var cellId = cell.id;
    var colspan = cell.getAttribute('colspan') ? parseInt(cell.getAttribute('colspan')) : 1;
    var rowspan = cell.getAttribute('rowspan') ? parseInt(cell.getAttribute('rowspan')) : 1;

    var turma = cellId.split('_')[1];
    var dia = cellId.split('_')[2];
    var day = switchDaytoNumber(dia);

    var horaInicio = parseInt(cellId.split('_')[3]);
    var aulaId = cell.getAttribute('data-aulaid');

    //Obter hora final
    var hora = horaInicio;
    var secondDigit;
    for (var i = 1; i <= rowspan; i++) {
        secondDigit = (hora / 10) % 10;
        if (secondDigit == 3) {
            hora += 70;
        }
        else {
            hora += 30;
        }
    }

    const turmasLista = curso.anos[0].turmas;
    var turmaIdsLista = [];

    var allAulas = document.querySelectorAll("tbody td:not(:first-child)[data-aulaid='" + aulaId + "']");

    if (allAulas.length > 1) { //Quando está apenas uma turma selecionada é preciso ir buscar o resto das aulas, no caso de ela ser uma teórica
        for (var i = 0; i < allAulas.length; i++) {
            var nextCell = allAulas[i];
            var nextCellId = nextCell.id;
            var nextCellTurma = nextCellId.split('_')[1];
            turmaIdsLista.push(nextCellTurma);
        }
    }
    else {
        var turmaIndex = turmasLista.indexOf(turma);

        for (var i = turmaIndex; i < turmaIndex + colspan; i++) {
            turmaIdsLista.push(turmasLista[i]);
        }
    }

    var uc = cell.querySelector('p.uc').id;

    var docentes = cell.querySelectorAll('p.docente');
    var salas = cell.querySelectorAll('p.sala');

    var docentesIds = [];
    for (var i = 0; i < docentes.length; i++) {
        docentesIds.push(docentes[i].id);
    }

    var salasIds = [];
    for (var i = 0; i < salas.length; i++) {
        salasIds.push(salas[i].id);
    }

    var formData = {
        csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
        projId: id,
        aulaId: aulaId,
        cadeiraId: uc,
        horaInicio: horaInicio,
        horaFim: hora,
        dia: day,
        turmasIds: turmaIdsLista,
        docentesIds: docentesIds,
        salasIds: salasIds
    };

    //console.log("Form data: ", formData);

    // create an AJAX call
    $.ajax({
        data: JSON.stringify(formData),
        type: 'POST', // GET or POST
        url: "/editturnos/" + id + "/makechanges",

        headers: {
            'X-CSRFToken': formData.csrfmiddlewaretoken
        },

        // on success
        success: function (response) {
            //TODO:mudar no horario

            //conflitos
            const conflicts = response.conflicts
            writeConflicts(conflicts)
        },
        // on error
        error: function (response, status, error) {
            console.log(response.responseText)
        }
    });
}

function swapPartialCells(p1, p2) {
    // Get the content of p1
    var p1Content = p1.innerHTML;

    // Get the content of p2
    var p2Content = p2.innerHTML;

    // Swap the content of p1 and p2
    p1.innerHTML = p2Content;
    p2.innerHTML = p1Content;

    // Optionally, swap other attributes like IDs and classes
    var p1Id = p1.id;
    var p2Id = p2.id;
    p1.id = p2Id;
    p2.id = p1Id;
}

function swapFullCells(firstCell, secondCell) {
    // Retrieve colspan and rowspan attributes, assigning default value 1 if not defined
    var colspanFirst = firstCell.getAttribute('colspan') ? parseInt(firstCell.getAttribute('colspan')) : 1;
    var rowspanFirst = firstCell.getAttribute('rowspan') ? parseInt(firstCell.getAttribute('rowspan')) : 1;

    var colspanSecond = secondCell.getAttribute('colspan') ? parseInt(secondCell.getAttribute('colspan')) : 1;
    var rowspanSecond = secondCell.getAttribute('rowspan') ? parseInt(secondCell.getAttribute('rowspan')) : 1;

    var class1 = firstCell.classList[0];
    var class2 = secondCell.classList[0];
    var id1 = firstCell.id;
    var id2 = secondCell.id;

    firstCell.setAttribute('class', class2);
    secondCell.setAttribute('class', class1);

    if (rowspanFirst == rowspanSecond && colspanFirst == colspanSecond) {
        //console.log("Inside 0 before");
        createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst >= colspanSecond) {
        //console.log("Inside 1 before");
        createCells(secondCell, colspanSecond - 1, rowspanSecond, 0);
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst <= colspanSecond) {
        if (rowspanFirst > rowspanSecond) {
            //console.log("Inside 2.0 before");
            createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
            createCells(secondCell, colspanSecond - 1, rowspanSecond, 0);
        }
        else {
            createCells(firstCell, colspanFirst - 1, rowspanSecond, 0);
        }
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst >= colspanSecond) {
        if (colspanFirst > colspanSecond) {
            //console.log("Inside 3.0 before");
            createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
            createCells(secondCell, colspanSecond - 1, rowspanSecond, 0);
        }
        else {
            //console.log("Inside 3.1 before");
            createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
        }
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst <= colspanSecond) {
        //console.log("Inside 4 before");
        createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
    }

    // Remove all div child elements from firstCell
    var firstDivChildren = firstCell.querySelectorAll('div');
    for (var i = 0; i < firstDivChildren.length; i++) {
        var divChild = firstDivChildren[i];
        firstCell.removeChild(divChild);
    }

    firstCell.setAttribute('id', id2);
    secondCell.setAttribute('id', id1);

    var parent1 = firstCell.parentNode;
    var sibling1 = firstCell.nextSibling;

    var parent2 = secondCell.parentNode;
    var sibling2 = secondCell.nextSibling;

    parent1.insertBefore(secondCell, sibling1);
    parent2.insertBefore(firstCell, sibling2);

    if (rowspanFirst == rowspanSecond && colspanFirst == colspanSecond) {
        //console.log("Inside 0");
        deleteCells(secondCell, colspanSecond - 1, rowspanSecond - 1);
    }
    else if (rowspanFirst > rowspanSecond && colspanFirst > colspanSecond) {
        //console.log("Inside 1");
        createCells(secondCell, colspanFirst - colspanSecond + 1, rowspanFirst, 1);
        deleteCells(firstCell, colspanFirst - colspanSecond, rowspanFirst - 1);
    }
    else if (rowspanFirst > rowspanSecond && colspanFirst <= colspanSecond) {
        //console.log("Inside 2");
        if (colspanFirst < colspanSecond) {
            console.log("Inside 2.0");
            deleteCells(secondCell, colspanSecond - colspanFirst, rowspanSecond - 1);
            deleteCells(firstCell, colspanFirst - 1, rowspanFirst - 1);
        }
        else {
            console.log("Inside 2.1");
            createCells(secondCell, colspanSecond - colspanFirst + 1, rowspanFirst, 1);
            deleteCells(firstCell, colspanSecond - colspanFirst, rowspanFirst - 1);
        }
    }
    else if (rowspanFirst <= rowspanSecond && colspanFirst > colspanSecond) {
        if (rowspanFirst < rowspanSecond) {
            //console.log("Inside 3.0");
            deleteCells(firstCell, colspanFirst - colspanSecond, rowspanFirst - 1);
            deleteCells(secondCell, colspanSecond - 1, rowspanSecond - 1);
        }
        else {
            //console.log("Inside 3.1");
            createCells(secondCell, colspanFirst - colspanSecond + 1, rowspanSecond, 1);
            deleteCells(firstCell, colspanFirst - colspanSecond, rowspanSecond - 1);
        }
    }
    else if (rowspanFirst <= rowspanSecond && colspanFirst <= colspanSecond) {
        //console.log("Inside 4");
        createCells(firstCell, colspanSecond - colspanFirst + 1, rowspanSecond, 1);
        deleteCells(secondCell, colspanSecond - colspanFirst, rowspanSecond - 1);
    }
}

function canSwap(cell1, cell2) {
    // Retrieve colspan and rowspan attributes, assigning default value 1 if not defined
    var colspanFirst = cell1.getAttribute('colspan') ? parseInt(cell1.getAttribute('colspan')) : 1;
    var originalcolspanFirst = cell1.getAttribute('data-originalcolspan') ? parseInt(cell1.getAttribute('data-originalcolspan')) : 1;
    var rowspanFirst = cell1.getAttribute('rowspan') ? parseInt(cell1.getAttribute('rowspan')) : 1;

    var colspanSecond = cell2.getAttribute('colspan') ? parseInt(cell2.getAttribute('colspan')) : 1;
    var originalcolspanSecond = cell2.getAttribute('data-originalcolspan') ? parseInt(cell2.getAttribute('data-originalcolspan')) : 1;
    var rowspanSecond = cell2.getAttribute('rowspan') ? parseInt(cell2.getAttribute('rowspan')) : 1;

    if (originalcolspanFirst != colspanFirst || originalcolspanSecond != colspanSecond) {
        console.log("A aula que está a tentar mover pertence a mais do que uma turma.\nPor favor mude para a vista de todas as turmas");

        if (!document.getElementById("tooltipcontainer")) {
            tooltipcontainer = document.createElement("div");
            tooltipcontainer.setAttribute("id", "tooltipcontainer");
            tooltipcontainer.style.position = "fixed";
            tooltipcontainer.style.left = Math.max(cell1.clientX + 10, 0) + "px";
            tooltipcontainer.style.top = Math.max(cell1.clientY - 25, 0) + "px";
            tooltipcontainer.style.zIndex = 999;

            tooltip = document.createElement("div");
            tooltip.style.position = "fixed";

            tooltip.style.width = "auto";
            tooltip.style.backgroundColor = "black";
            tooltip.style.color = "#fff";
            tooltip.style.padding = "5px";
            tooltip.style.zIndex = "999";
            tooltip.style.fontSize = "13px";
            tooltip.textContent = "A aula que está a tentar mover pertence a mais do que uma turma.\nPor favor mude para a vista de todas as turmas";

            tooltipcontainer.appendChild(tooltip);

            tableVistas = document.getElementById("table_vistas").parentNode;
            tableVistas.insertBefore(tooltipcontainer, tableVistas.firstChild);
        }

        return false;
    }

    var swap;

    if (rowspanFirst == rowspanSecond && colspanFirst == colspanSecond) {
        swap = true;
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst >= colspanSecond) {
        //console.log("Inside 1 check");
        swap = checkIfSwapPossible(cell2, cell1, colspanFirst - colspanSecond, rowspanFirst - 1);
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst < colspanSecond) {
        //console.log("Inside 2 check");
        swap = checkIfSwapPossible(cell1, cell2, colspanSecond - colspanFirst, rowspanSecond - 1) && checkIfSwapPossible(cell2, cell1, colspanSecond - colspanFirst, rowspanFirst - 1);
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst >= colspanSecond) {
        //console.log("Inside 3 check");
        swap = checkIfSwapPossible(cell1, cell2, colspanFirst - colspanSecond, rowspanSecond - 1) && checkIfSwapPossible(cell2, cell1, colspanFirst - colspanSecond, rowspanFirst - 1);
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst < colspanSecond) {
        //console.log("Inside 4 check");
        swap = checkIfSwapPossible(cell1, cell2, colspanSecond - colspanFirst, rowspanSecond - 1);
    }

    //console.log("Swap: ", swap);
    return swap;
}

function checkIfSwapPossible(cell, cell2, cellsRight, cellsBottom) {
    /*
    console.log("CHECK SWAP FOR CELL: ", cell);
    console.log("      Cells right: ", cellsRight);
    console.log("      Cells bottom: ", cellsBottom);*/
    const turmasLista = curso.anos[0].turmas;

    var cellId = cell.id;
    var cellTurma = cellId.split("_")[1];
    var turmaIndex = turmasLista.indexOf(cellTurma);

    var colspan = cell.getAttribute('colspan') ? parseInt(cell.getAttribute('colspan')) : 1;
    var rowspan = cell.getAttribute('rowspan') ? parseInt(cell.getAttribute('rowspan')) : 1;

    for (var i = 0; i <= cellsBottom; i++) {
        count = cellsRight;
        while (count >= 0) {
            if (i < rowspan && count < colspan) {
                count--;
                continue;
            }

            var newCellTurma = turmasLista[turmaIndex + count];
            var newCellId = cellId.split("_")[0] + '_' + newCellTurma + '_' + cellId.split("_")[2] + '_' + cellId.split("_")[3];

            //console.log("A verificar: ", newCellId);
            //console.log("Children: ", document.getElementById(newCellId).children);

            var newCell = document.querySelector("td#" + newCellId);

            if (!newCell)
                return false;

            if (newCellId == cell2.id)
                return true;

            var content = newCell.innerHTML;
            content = content.replace(/\s/g, "");

            if (content != '') {
                return false;
            }

            count--;
        }
        var hora = parseInt(cellId.split('_')[3]);

        secondDigit = (hora / 10) % 10;
        if (secondDigit == 3) {
            hora += 70;
        }
        else {
            hora += 30;
        }

        cellId = cellId.split('_')[0] + "_" + cellId.split('_')[1] + "_" + cellId.split('_')[2] + "_" + hora; //id da célula seguinte pertencente à mesma aula
    }
    return true;
}

function displayBlocosVermelhosTurma(turma, display) {
    if (!display) {
        const redCellsTd = document.querySelectorAll('td[style="background-color: red; opacity: 0.6;"]');
        const redCellsDiv = document.querySelectorAll('div[style="background-color: red; opacity: 0.6;"]');

        for (var i = 0; i < redCellsTd.length; i++) {
            redCellsTd[i].setAttribute("style", "");
        }

        for (var i = 0; i < redCellsDiv.length; i++) {
            redCellsDiv[i].setAttribute("style", "");
        }
        return;
    }

    console.log("Turma: ", turma);
    // Make the asynchronous request
    $.ajax({
        url: '/blocosturma/',  // Update with your actual URL
        type: 'GET',
        data: { 'turma': turma, 'projId': projId },
        success: function (data) {
            displayBlocosVermelhos(data.blocos, true, turma);

        },
        error: function (xhr, textStatus, error) {
            // Handle any errors
        }
    });
}

function displayBlocosVermelhosGlobal(className, id, display) {
    var blocosVermelhos;
    if (className == 'docente selected' || className == 'docente') {
        const allDocentes = curso.anos[0].docentes;

        var docente;
        for (var i = 0; i < allDocentes.length; i++) {
            if (allDocentes[i].numMecanografico == id) {
                docente = allDocentes[i];
                break;
            }
        }

        if (docente == null)
            return;

        blocosVermelhos = docente.blocos;
        displayBlocosVermelhos(blocosVermelhos, display, 'any');
    }
    else if (className == 'sala selected' || className == 'sala') {
        const allSalas = curso.salas;

        var sala;
        for (var i = 0; i < allSalas.length; i++) {
            if (allSalas[i].numero == id) {
                sala = allSalas[i];
                break;
            }
        }

        if (sala == null)
            return;

        blocosVermelhos = sala.blocos;
        displayBlocosVermelhos(blocosVermelhos, display, 'any');
    }
}

function displayBlocosVermelhos(blocosVermelhos, display, turma) {
    console.log("Display: ", display);
    //console.log("Blocos: ", blocosVermelhos);
    for (var i = 0; i < blocosVermelhos.length; i++) {
        var bloco = blocosVermelhos[i];
        console.log("Bloco: ", bloco);
        var dia = bloco.diaSemana;
        console.log("Dia: ", dia);
        var substring = dia.toLowerCase() + "_" + bloco.hora;
        var targetElements, targetElements2;

        if (turma == 'any') {
            //Blocos vermelhos que estarão em células já preenchidas
            var selector = "div[id*=" + substring + "]";
            targetElements = document.querySelectorAll(selector);

            //Blocos vermelhos que estarão em células vazias
            var selector2 = "td:not(:has(div))[id*=" + substring + "]";
            targetElements2 = $(selector2);
        }
        else {
            //Blocos vermelhos que estarão em células já preenchidas
            var selector = 'div[id*="' + substring + '"]:has([id*="' + turma + '"])';
            targetElements = $(selector);

            //Blocos vermelhos que estarão em células vazias
            var selector2 = 'td:not(:has(div))[id*="' + substring + '"][id*="' + turma + '"]';
            targetElements2 = $(selector2);
        }

        //Blocos vermelhos que estão em células já preenchidas
        for (var j = 0; j < targetElements.length; j++) {
            var element = targetElements[j];

            if (display) {
                element.style.backgroundColor = "red";
                element.style.border = "1px solid white";
                element.style.opacity = 0.6;
            }
            else {
                element.style.backgroundColor = "#fff";
                element.style.backgroundColor = "transparent";
                element.style.border = "none";
                element.style.opacity = 1;
            }
        }

        //Blocos vermelhos que estão em células vazias
        for (var j = 0; j < targetElements2.length; j++) {
            var element = targetElements2[j];
            if (display) {
                element.style.backgroundColor = "red";
                element.style.opacity = 0.6;
            }
            else {
                element.style.backgroundColor = "#fff";
                element.style.opacity = 1;
            }
        }
    }
}