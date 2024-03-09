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
                cell.appendChild(p_element);
                cell.setAttribute("rowspan", aula.duracao);
            }
        }
    }
}

function fillUcs(ano) {
    const colorDictionary = {
        0: ["#FFDABF", "#FFEED9"],   // Light Orange
        1: ["#EAEAB5", "#F4F4CE"],  // Light Olive
        2: ["#CCFFCC", "#E6FFE6"],   // Light Green
        3: ["#FFFFCC", "#FFFFE6"],   // Light Yellow
        4: ["#fcdcdc", "#f2e1e1"],  // Misty Rose
        5: ["#FFCCFF", "#FFE6FF"],   // Light Magenta
        6: ["#FFCCCC", "#FFE6E6"],   // Light Red
        7: ["#E7CEFF", "#F0DFFF"],   // Light Purple
        8: ["#BDFFBD", "#D9FFD9"],   // Light Dark Green
        9: ["#FAB0B0", "#FFCCCC"],  // Light Coral
        10: ["#BDBDFF", "#D9D9FF"],  // Light Navy
        11: ["#FFBDBD", "#FFD9D9"],   // Light Maroon
        12: ["#BDFEFF", "#D9FFFF"],  // Light Teal
        13: ["#D9D9D9", "#ECECEC"],  // Light Gray
        14: ["#D8D8D8", "#EAEAEA"],  // Light Silver
        15: ["#FFEBC6", "#FFF5E0"],  // Light Apricot
        16: ["#DEFFB3", "#EFFFCC"],  // Light Lime
        17: ["#C1F0FF", "#D6F7FF"],  // Light Sky Blue
        18: ["#FFD1D9", "#FFE0E8"],  // Light Pink
        19: ["#C6E6E9", "#D6EBED"],  // Light Powder Blue
        20: ["#E6D9E6", "#F0EAF0"],  // Light Thistle
        21: ["#FFEC96", "#FFF5CC"],  // Light Gold
        22: ["#FFCDD6", "#FFE8ED"],  // Light Pink
        23: ["#FFEED9", "#FFF7E6"],  // Light Bisque
        24: ["#CCCCFF", "#E6E6FF"],   // Light Blue
        25: ["#E0FFFF", "#F0FFFF"],  // Cyan / Aqua
        26: ["#B8F4D8", "#CCFCE3"],  // Aquamarine
        27: ["#FFF8E7", "#FFFDF0"],  // Light Blanched Almond
        28: ["#C0FAC0", "#D9FFD9"],  // Light Green
        29: ["#B0E0F8", "#CCE8FF"],  // Light Sky Blue
        30: ["#F0C8F0", "#F7DFF7"],  // Plum
        31: ["#FFC4B3", "#FFD9CA"],  // Light Salmon
        32: ["#5CD8B2", "#8CF5CB"],  // Light Sea Green
        33: ["#A3AEB9", "#C1CDD3"],  // Light Slate Gray
        34: ["#F0FFFF", "#F5FFFF"],  // Light Cyan
        35: ["#F5FFF5", "#FAFFFA"],  // Honeydew
        36: ["#FFD1D9", "#FFE0E8"],  // Light Pink
        37: ["#F0F0FF", "#F5F5FF"],  // Lavender
        38: ["#FFF5FB", "#FFFAFF"],  // Lavender Blush
        39: ["#CCFFFF", "#E6FFFF"],   // Light Cyan
        40: ["#B3F586", "#D2FFA0"],  // Lawn Green
        41: ["#FFFCE6", "#FFFFF0"],  // Lemon Chiffon
        42: ["#C6E6F5", "#D6ECF7"],  // Light Blue
        43: ["#FAB0B0", "#FFCCCC"]   // Light Coral
    };
    const allUCs = curso.ucs;
    let ucAnoSet = new Set();
    let ucAnoBool = false;
    let turmasSet = new Set();

    for (let i = 0; i < allUCs.length; i++) {
        var uc = allUCs[i];
        var aulas = uc.aulas; //FORMATO -> [Aula(id, horaInicial, duracao, diaSemana, isTeorica)]

        ucAnoBool = false;
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
            ucAnoBool = true;

            turmas = turmas[ano];

            var dia = aula.diaSemana.toLowerCase();
            var hora = aula.horaInicial;

            for (let k = 0; k < turmas.length; k++) {
                var turma = turmas[k];
                turmasSet.add(turma);

                var idString = "turma_" + turma + "_" + dia + "_" + hora;   //id da célula a que pertence a aula


                var cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); //célula a que pertence a aula
                if (cell == null) {
                    continue;
                }

                cell.setAttribute("data-aulaID", aula.id);

                var deleteHorizontal = 0;
                var deleteVertical = aula.duracao - 1;
                if (aula.isTeorica) {
                    deleteHorizontal = turmas.length - 1;
                }

                deleteCells(cell, deleteHorizontal, deleteVertical);

                var sigla = uc.sigla.slice(0, uc.sigla.indexOf("("));
                var p_element = document.createElement("p");
                p_element.classList.add("uc");
                p_element.id = uc.codigo;
                p_element.innerHTML = sigla;
                cell.appendChild(p_element);
                cell.setAttribute("rowspan", aula.duracao);
                cell.setAttribute("data-semanas", aula.semanaInicial + ' - ' + aula.semanaFinal);

                if (aula.isTeorica) {
                    cell.setAttribute("colspan", turmas.length);
                    cell.setAttribute("data-originalcolspan", turmas.length);
                    cell.setAttribute("style", "border: 2px solid black;");
                    cell.setAttribute("style", "background-color: " + colorDictionary[ucAnoSet.size][1]);
                    cell.setAttribute("data-teorica", 1)
                    break;
                }

                cell.setAttribute("style", "border: 2px solid black;");
                cell.setAttribute("style", "background-color: " + colorDictionary[ucAnoSet.size][0]);
                cell.setAttribute("data-teorica", 0);
            }
        }
        if (ucAnoBool) ucAnoSet.add(uc);
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

    var top = 0;

    for (var i = 0; i <= cellsBottom; i++) {
        var row = table.rows[rowIndex + i];
        count = cellsRight;
        while (count >= 0) {
            if (i == 0 && count == 0) {
                break;
            }
            var cellToDelete = row.cells[cellIndex + count];
            //console.log("Cell deleted: ", cellToDelete);
            var idToDelete = cellToDelete.id;
            var div = document.createElement("div");
            div.classList.add("inside_tds");
            div.id = idToDelete;

            var rect = cellToDelete.getBoundingClientRect();
            var width = rect.width;
            var height = rect.height;

            if (count == cellsRight) {
                left = cellsRight * width;
            }
            else {
                left -= width;
            }

            div.setAttribute("style", "left: " + left + "px; top: " + top + "px; height: " + height + "px; width: " + width + "px;");
            originalCell.style.position = "relative"; // Add this line
            originalCell.appendChild(div);

            row.deleteCell(cellIndex + count);
            count--;
        }

        top += 40;

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

function fillDocentes(ano) {
    const allDocentes = curso.anos[0].docentes;
    for (let i = 0; i < allDocentes.length; i++) {
        var docente = allDocentes[i];
        var aulas = docente.aulas;

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
                p_element.classList.add("docente");
                p_element.id = docente.numMecanografico;
                p_element.innerHTML = docente.abreviacao;
                cell.appendChild(p_element);
                cell.setAttribute("rowspan", aula.duracao);
            }
        }
    }
}

function mergeTurnos() {
    const cells = $("#table_vistas").find("td:not(:first-child):has(p)");

    console.log(cells)

    cells.forEach(function (cell) {
        var colspan = parseInt(cell.getAttribute('colspan'));
        var originalColspan = parseInt(cell.getAttribute('data-originalcolspan'));

        if (colspan === originalColspan || !colspan)
            return;

        var aulaId = cell.getAttribute('data-aulaid');
        var nextSibling = document.querySelector("tbody td:not(:first-child).turno2[data-aulaid='" + aulaId + "']");
        if (nextSibling) {
            nextSibling.remove();
        }
        cell.setAttribute('colspan', originalColspan);
    })
}

function unmergeTurnos() {
    const cells = $('#table_vistas td:not(:first-child):has(p)');
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
    const cells = $("#table_vistas").find("td:not(:first-child):has(p)");


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
    const cells = $("#table_vistas").find("td:not(:first-child):has(p)");

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

    // Check if the target element is the td itself or a descendant of the td
    if (targetElement === td || $.contains(td, targetElement)) {
        // Unselect any selected p element
        const selectedP = $('td:not(:first-child) p.selected');
        if (selectedP.length) {
            showEditBarOptions(false);
            selectedP.removeClass('selected');
            displayBlocosVermelhosGlobal(selectedP.attr('class'), selectedP.attr('id'), false);
        }

        if ($(td).hasClass('selected')) {
            showEditBarOptions(false)
            $(td).removeClass('selected');
            return;
        }

        const prevSelectedCell = $('td:not(:first-child).selected');
        // Caso já exista uma célula selecionada, então é preciso trocá-las
        if (prevSelectedCell.length === 1) {
            // td / prevSelectedCell
            var prevCell = document.querySelector("td:not(:first-child).selected");

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
                // Handle the error that occurred in canSwap or swapFullCells
                console.error("An error occurred in canSwap or swapFullCells:", error);
                console.log("Reverting changes made to the table");
                swapFullCells(td, prevCell);
            }

            showEditBarOptions(false);
        }

        // remove class from all other td
        document.querySelectorAll("td:not(:first-child)").forEach(td => {
            showEditBarOptions(false);
        });

        $('td:not(:first-child)').removeClass('selected');

        // add class to clicked td
        $(td).addClass('selected');

        if (td.children.length > 0) {
            showEditBarOptions(true);
            selectedCellSelectSideBar(targetElement, false);
        }
        else showEditBarOptions(false);
    }
});



$(document).on('mouseenter', '#table_vistas td:not(:first-child):has(p)', function (event) {
    // MUDAR UCS
    //console.log("Entered cell");
    const td = this;
    var siglaUC = td.querySelector(".uc").textContent;
    for (var i = 0; i < curso.ucs.length; i++) {
        var uc_sigla = curso.ucs[i].sigla;
        var indexOfParenthesis = uc_sigla.indexOf("(");
        if (indexOfParenthesis !== -1) {
            uc_sigla = uc_sigla.substring(0, indexOfParenthesis);
        }
        if (siglaUC == uc_sigla) {
            var name = curso.ucs[i].nome;
            td.querySelector(".uc").textContent = name;
            td.querySelector(".uc").style.whiteSpace = "nowrap"; // Set white-space to nowrap
        }
    }
    // MUDAR DOCENTES
    var siglasDocentes = td.querySelectorAll(".docente")
    for (var j = 0; j < siglasDocentes.length; j++) {
        siglaDocente = siglasDocentes[j].textContent;
        for (var i = 0; i < curso.docentes.length; i++) {
            var doc_sigla = curso.docentes[i].abreviacao;
            if (siglaDocente == doc_sigla) {
                var name = curso.docentes[i].nome;
                td.querySelectorAll(".docente")[j].textContent = name;
                td.querySelectorAll(".docente")[j].style.whiteSpace = "nowrap"; // Set white-space to nowrap
            }
        }
    }
});

$(document).on('mouseleave', '#table_vistas td:not(:first-child):has(p)', function (event) {
    // MUDAR UCS
    const td = this;
    var nameUC = td.querySelector(".uc").textContent;

    for (var i = 0; i < curso.ucs.length; i++) {
        var this_name = curso.ucs[i].nome;
        if (nameUC == this_name) {
            var siglaUC = curso.ucs[i].sigla;
            var indexOfParenthesis = siglaUC.indexOf("(");
            if (indexOfParenthesis !== -1) {
                siglaUC = siglaUC.substring(0, indexOfParenthesis);
            }
            td.querySelector(".uc").textContent = siglaUC;
        }
    }
    var nomes = td.querySelectorAll(".docente");
    for (var j = 0; j < nomes.length; j++) {
        nome = nomes[j].textContent;
        for (var i = 0; i < curso.docentes.length; i++) {
            var doc_nome = curso.docentes[i].nome;
            if (nome == doc_nome) {
                var sigla = curso.docentes[i].abreviacao;
                td.querySelectorAll(".docente")[j].textContent = sigla;
            }
        }
    }
});


$(document).on('click', 'td:not(:first-child) p', function (event) {
    event.stopPropagation(); // Prevent click event from propagating to the td element

    const p = this;

    // Unselect any selected td element
    const selectedTD = $('td:not(:first-child).selected');
    if (selectedTD.length) {
        selectedTD.removeClass('selected');
        showEditBarOptions(false);
    }

    if ($(p).hasClass('selected')) {
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

    // add class to clicked p
    $(p).addClass('selected');
    showEditBarOptions(true);
    displayBlocosVermelhosGlobal(p.className, p.id, true);
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

    console.log("Form data: ", formData);

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
    var aulaId1 = firstCell.getAttribute("data-aulaid");
    var aulaId2 = secondCell.getAttribute("data-aulaid");

    /*
    var allAulas1 = document.querySelector("tbody td:not(:first-child)[data-aulaid='" + aulaId1 + "']");
    var allAulas2 = document.querySelector("tbody td:not(:first-child)[data-aulaid='" + aulaId2 + "']");

    for(var i=0; i<allAulas1.length; i++) {
        var cell = allAulas1[i];
        var cellId = cell.id;
        if(id1 === cellId)
            continue;

        swapFullCells()
    }*/

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
        //console.log("Inside 2 before");
        createCells(firstCell, colspanFirst - 1, rowspanSecond, 0);
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst >= colspanSecond) {
        //console.log("Inside 3 before");
        createCells(secondCell, colspanSecond - 1, rowspanFirst, 0);
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst < colspanSecond) {
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
        createCells(secondCell, colspanSecond - colspanFirst + 1, rowspanFirst, 1);
        deleteCells(firstCell, colspanSecond - colspanFirst, rowspanFirst - 1);
    }
    else if (rowspanFirst <= rowspanSecond && colspanFirst > colspanSecond) {
        //console.log("Inside 3");
        createCells(secondCell, colspanFirst - colspanSecond + 1, rowspanSecond, 1);
        deleteCells(firstCell, colspanFirst - colspanSecond, rowspanSecond - 1);
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
    var rowspanFirst = cell1.getAttribute('rowspan') ? parseInt(cell1.getAttribute('rowspan')) : 1;

    var colspanSecond = cell2.getAttribute('colspan') ? parseInt(cell2.getAttribute('colspan')) : 1;
    var rowspanSecond = cell2.getAttribute('rowspan') ? parseInt(cell2.getAttribute('rowspan')) : 1;

    var swap;

    if (rowspanFirst >= rowspanSecond && colspanFirst >= colspanSecond) {
        //console.log("Inside 1 check");
        swap = checkIfSwapPossible(cell2, colspanFirst - colspanSecond, rowspanFirst - 1);
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst < colspanSecond) {
        //console.log("Inside 2 check");
        swap = checkIfSwapPossible(cell1, colspanSecond - colspanFirst, rowspanSecond - 1) && checkIfSwapPossible(cell2, colspanSecond - colspanFirst, rowspanFirst - 1);
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst >= colspanSecond) {
        //console.log("Inside 3 check");
        swap = checkIfSwapPossible(cell1, colspanFirst - colspanSecond, rowspanSecond - 1) && checkIfSwapPossible(cell2, colspanFirst - colspanSecond, rowspanFirst - 1);
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst < colspanSecond) {
        //console.log("Inside 4 check");
        swap = checkIfSwapPossible(cell1, colspanSecond - colspanFirst, rowspanSecond - 1);
    }

    console.log("Swap: ", swap);
    return swap;
}

function checkIfSwapPossible(cell, cellsRight, cellsBottom) {
    //console.log("CHECK SWAP FOR CELL: ", cell);
    //console.log("      Cells right: ", cellsRight);
    //console.log("      Cells bottom: ", cellsBottom);
    const turmasLista = curso.anos[0].turmas;

    var cellId = cell.id;
    var cellTurma = cellId.split("_")[1];
    var turmaIndex = turmasLista.indexOf(cellTurma);

    for (var i = 0; i <= cellsBottom; i++) {
        count = cellsRight;
        while (count >= 0) {
            if (i == 0 && count == 0) {
                break;
            }

            var newCellTurma = turmasLista[turmaIndex + count];
            var newCellId = cellId.split("_")[0] + '_' + newCellTurma + '_' + cellId.split("_")[2] + '_' + cellId.split("_")[3];

            //console.log("A verificar: ", newCellId);
            //console.log("Children: ", document.getElementById(newCellId).children);

            if (!document.getElementById(newCellId) || document.getElementById(newCellId).children.length !== 0) {
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

function displayBlocosVermelhosGlobal(className, id, display) {
    var blocosVermelhos;
    if (className == 'docente') {
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
        displayBlocosVermelhos(blocosVermelhos, display);
    }
    else if (className == 'sala') {
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
        displayBlocosVermelhos(blocosVermelhos, display);
    }
}

function displayBlocosVermelhos(blocosVermelhos, display) {
    for (var i = 0; i < blocosVermelhos.length; i++) {
        var bloco = blocosVermelhos[i];
        var substring = bloco.diaSemana.toLowerCase() + "_" + bloco.hora;

        //Blocos vermelhos que estarão em células já preenchidas
        var selector = "div[id*=" + substring + "]";
        var targetElements = document.querySelectorAll(selector);

        //Blocos vermelhos que estarão em células vazias
        var selector2 = "td:not(:has(div))[id*=" + substring + "]";
        var targetElements2 = $(selector2);

        // Iterate through the target elements and apply the CSS style
        for (var j = 0; j < targetElements.length; j++) {
            var element = targetElements[j];

            if (display) {
                element.style.backgroundColor = "red";
                element.style.opacity = 0.6;
            }
            else {
                element.style.backgroundColor = "#fff";
                element.style.opacity = 1;
            }
        }

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