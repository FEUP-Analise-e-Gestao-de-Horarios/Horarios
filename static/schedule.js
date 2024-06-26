/**
 * Preenche as aulas no horário com base no ano.
 *
 * @param {number} ano - O ano do curso selecionado para o horário.
 * @returns {null} Não retorna qualquer valor.
 */
function fillUcs(ano) {
    const allUCs = curso.ucs;
    const ucAnoSet = new Set();
    const turmasSet = new Set();
    let ucAnoBool = false;

    const relevantUcs = allUCs.filter(uc =>
        uc.anos.includes(ano)
    );

    relevantUcs.forEach(sortAulasByTurmasAndDuracao);
    relevantUcs.sort((ucA, ucB) => {
        const weightA = calculateUcWeight(ucA);
        const weightB = calculateUcWeight(ucB);
        return weightA - weightB;
    })

    for (let i = 0; i < relevantUcs.length; i++) {
        let uc = relevantUcs[i];
        let aulas = uc.aulas; //FORMATO -> [Aula(id, horaInicial, duracao, diaSemana, isTeorica)]
        ucAnoBool = false;

        for (let j = 0; j < aulas.length; j++) {
            let aula = aulas[j];

            let turmas = aula.turmas; //FORMATO -> {ano: [codigoTurma]}
            if (!(ano in turmas)) { //Caso não tenha turmas do ano em que a tabela está
                continue;
            }
            ucAnoBool = true;

            turmas = turmas[ano];

            const dia = aula.diaSemana.toLowerCase();
            const hora = aula.horaInicial;

            let turmaGroups = [];
            let currentGroup = [];

            if (turmas.length > 0) {
                currentGroup.push(turmas[0]);

                for (let i = 1; i < turmas.length; i++) {
                    turmasSet.add(turmas[i - 1]);
                    turmasSet.add(turmas[i]);
                    let turmaNumber1 = Number(turmas[i].match(/\d+$/)[0]);
                    let turmaNumber2 = Number(turmas[i - 1].match(/\d+$/)[0]);

                    if (turmaNumber1 === turmaNumber2 + 1) {
                        currentGroup.push(turmas[i]);
                    } else {
                        turmaGroups.push(currentGroup);
                        currentGroup = [turmas[i]];
                    }
                }
                turmaGroups.push(currentGroup);
            }

            for (let k = 0; k < turmaGroups.length; k++) {
                let group = turmaGroups[k];
                let idString = "turma_" + group[0] + "_" + dia + "_" + hora;   //id da célula a que pertence a aula

                let cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); //célula a que pertence a aula
                if (cell == null) {
                    continue;
                }

                let turmasString = turmas.join(",");
                cell.setAttribute("data-turmas", turmasString);
                cell.setAttribute("data-aulaID", aula.id);

                if (turmaGroups.length > 1) {
                    let groupString = group.join(',');
                    cell.setAttribute("data-group", groupString);
                }

                let deleteHorizontal = 0;
                let deleteVertical = aula.duracao - 1;
                if (aula.isTeorica) {
                    deleteHorizontal = group.length - 1;
                } else {
                    let turmasLista = curso.anos[0].turmas;
                    let turmaIndex = turmasLista.indexOf(group[0]);
                    for (let t = 0; t + turmaIndex < turmasLista.length; t++) {
                        if (group[t] == turmasLista[turmaIndex + t]) {
                            deleteHorizontal += 1;
                        }
                        else {
                            break;
                        }
                    }
                    deleteHorizontal -= 1;
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
                cell.setAttribute("data-si", aula.semanaInicial);
                cell.setAttribute("data-sf", aula.semanaFinal);

                cell.setAttribute("colspan", group.length);
                cell.setAttribute("data-originalcolspan", group.length);
                cell.setAttribute("style", "border: 2px solid black;");

                if (aula.isTeorica) {
                    cell.setAttribute("style", "background-color: " + window.colorDictionary[ucAnoSet.size][1]);
                    cell.setAttribute("data-teorica", 1)
                }
                else {
                    cell.setAttribute("style", "background-color: " + window.colorDictionary[ucAnoSet.size][0]);
                    cell.setAttribute("data-teorica", 0);
                }
            }
        }
        if (ucAnoBool) ucAnoSet.add(uc);
    }
    setSidebarUCs(ucAnoSet);
    setSidebarTurmas(turmasSet);
}

function sortAulasByTurmasAndDuracao(uc) {
    uc.aulas.sort((a, b) => {
        const turmasA = a.turmas[ano] ? a.turmas[ano].length : 0;
        const turmasB = b.turmas[ano] ? b.turmas[ano].length : 0;
        if (turmasA === turmasB) {
            return a.duracao - b.duracao;
        }
        return turmasA - turmasB;
    });
}

function calculateUcWeight(uc) {
    return uc.aulas.reduce((acc, aula) => {
        const turmasLength = aula.turmas[ano] ? aula.turmas[ano].length : 0;
        return acc + aula.duracao * turmasLength;
    }, 0);
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

/**
 * Preenche o campo da sala nas células do horário
 * 
 * @param {number} ano - O ano para o qual devem ser geradas as salas
 * @returns {null} - Não retorna qualquer valor
 */
function fillSalas(ano) {
    const allSalas = curso.salas;

    for (let i = 0; i < allSalas.length; i++) {
        let sala = allSalas[i];
        let aulas = sala.aulas;

        for (let j = 0; j < aulas.length; j++) {
            let aula = aulas[j];

            let turmas = aula.turmas; //FORMATO -> {ano: [codigoTurma]}
            if (!(ano in turmas)) { //Caso não tenha turmas do ano em que a tabela está
                continue;
            }

            turmas = turmas[ano];
            let dia = aula.diaSemana.toLowerCase();
            let hora = aula.horaInicial;

            for (let k = 0; k < turmas.length; k++) {
                let turma = turmas[k];

                const idString = "turma_" + turma + "_" + dia + "_" + hora;

                let cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); //célula a que pertence a aula
                if (cell == null) {
                    continue;
                }

                const p_element = document.createElement("p");
                p_element.classList.add("sala");
                p_element.id = sala.numero;
                p_element.innerHTML = sala.numero;
                p_element.style.display = "inline-block";
                const br = document.createElement("br");
                cell.appendChild(br);
                cell.appendChild(p_element);
                cell.setAttribute("rowspan", aula.duracao);
            }
        }
    }
}

/**
 * Encontra a posição horizontal de uma célula numa linha da tabela.
 *
 * @param {Array} row - A linha da tabela.
 * @param {string} cellToInsertID - ID da célula a inserir.
 * @returns {number} - A posição horizontal da célula a inserir.
 */
function findHorizontalPosition(row, cellToInsertID) {
    const day = cellToInsertID.split('_')[2];
    const turma = cellToInsertID.split('_')[1];
    let rowIndex = 0;

    const turmasLista = curso.anos[0].turmas;
    const dias = ["segunda", "terça", "quarta", "quinta", "sexta"];

    for (let i = 0; i < dias.length; i++) {
        let turmasDia = 0;
        for (let j = 0; j < row.length; j++) {
            const cellId = row[j].id;
            const cellDay = cellId.split('_')[2];
            const cellTurma = cellId.split('_')[1];
            const cellTurmaIndex = turmasLista.indexOf(cellTurma);
            const turmaIndex = turmasLista.indexOf(turma);

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

/**
 * Cria novas células na tabela.
 * 
 * @param {HTMLElement} cell - A célula a partir da qual devem ser criadas as novas.
 * @param {number} cellsRight - Número de células a criar para a direita.
 * @param {number} cellsBottom - Número de células a criar para baixo.
 * @param {number} startingVal - O valor inicial para a criação das células.
 * @returns {null} Não retorna qualquer valor.
 */
function createCells(cell, cellsRight, cellsBottom, startingVal) {
    const table = document.getElementById("table_vistas");
    const turmasLista = curso.anos[0].turmas;

    const rowspan = cell.getAttribute('rowspan') ? parseInt(cell.getAttribute('rowspan')) : 1;

    const rowIndex = cell.parentNode.rowIndex;
    const cellClass = cell.classList[0];
    let cellId = cell.id;
    const cellTurma = cellId.split("_")[1];
    const turmaIndex = turmasLista.indexOf(cellTurma);

    for (let i = 0; i < cellsBottom; i++) {
        const row = table.rows[rowIndex + i];
        for (let j = startingVal; j <= cellsRight; j++) {
            if ((startingVal == 0 && i == 0 && j == 0) || (startingVal == 1 && i < rowspan && j == 1))
                continue;
            let index = (turmaIndex + j - startingVal + turmasLista.length) % turmasLista.length;
            let newCellTurma = turmasLista[index];
            let newCellId = cellId.split("_")[0] + '_' + newCellTurma + '_' + cellId.split("_")[2] + '_' + cellId.split("_")[3];

            let newCellRowIndex = findHorizontalPosition(row.cells, newCellId);
            let newCell = row.insertCell(newCellRowIndex);
            newCell.classList.add(cellClass);
            newCell.setAttribute('id', newCellId);
        }
        let hora = parseInt(cellId.split('_')[3]);

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

/**
 * Elimina células de uma tabela, começando por uma dada célula.
 * 
 * @param {HTMLElement} cell - A célula onde a eliminação deve começar.
 * @param {number} cellsRight - Número de células a eliminar para a direita
 * @param {number} cellsBottom - Número de células a eliminar para baixo.
 */
function deleteCells(cell, cellsRight, cellsBottom) {
    const table = document.getElementById("table_vistas");
    let originalCell = cell;

    const rowIndex = cell.parentNode.rowIndex;
    let cellIndex = cell.cellIndex;
    let idCell = cell.id;

    let firstRow = table.rows[1];
    let top = 0;

    for (let i = 0; i <= cellsBottom; i++) {
        let row = table.rows[rowIndex + i];
        let height;
        let count = cellsRight;
        while (count >= 0) {
            let cellToDelete = row.cells[cellIndex + count];
            let cellToGetHeight = row.cells[0];
            let cellToGetWidth = firstRow.cells[cellIndex + count];
            let idToDelete = cellToDelete.id;
            let div = document.createElement("div");
            div.classList.add("inside_tds");
            div.id = idToDelete;

            const rectHeight = cellToGetHeight.getBoundingClientRect();
            const rectWidth = cellToGetWidth.getBoundingClientRect();

            let width = rectWidth.width;
            height = rectHeight.height;

            if (count == cellsRight) {
                left = cellsRight * width;
            }
            else {
                left -= width;
            }

            div.setAttribute("style", "left: " + left + "px; top: " + top + "px; height: " + height + "px; width: " + width + "px;");
            originalCell.style.position = "relative";
            originalCell.appendChild(div);

            if (i == 0 && count == 0) {
                break;
            }

            row.deleteCell(cellIndex + count);
            count--;
        }

        top += height;

        let hora = parseInt(idCell.split('_')[3]);

        secondDigit = (hora / 10) % 10;
        if (secondDigit == 3) {
            hora += 70;
        }
        else {
            hora += 30;
        }

        if (i != cellsBottom) {
            idCellSplit = idCell.split('_');
            idCell = idCellSplit[0] + "_" + idCellSplit[1] + "_" + idCellSplit[2] + "_" + hora; //id da célula seguinte pertencente à mesma aula
            cell = document.querySelector("td[id='" + idCell + "']");
            if (!cell) break;
            cellIndex = cell.cellIndex;
        }
    }
}

/**
 * Faz o display de todas as aulas do horário.
 * 
 * @returns {null} Não retorna qualquer valor.
 */
function displayAllAulas() {
    const allTurmas = document.querySelectorAll("tbody [id*=turma_]");
    allTurmas.forEach(cell => {
        cell.style.display = '';
        if (cell.hasAttribute("data-originalcolspan")) {
            cell.colSpan = parseInt(cell.getAttribute("data-originalcolspan"), 10);
        }
    });
}

/**
 * Faz o display de todas as aulas de um dado turno.
 * 
 * @param {string[]} turmas - Array de turmas para as quais deve ser feito o display.
 * @returns {null} Não retorna qualquer valor.
 */
function displayTurmasForTurno(turmas) {
    const allTurmaCells = document.querySelectorAll("tbody [id*=turma_]");
    allTurmaCells.forEach(cell => {
        cell.style.display = 'none';

        // Função auxiliar para processar células baseada no nome do atributo
        const processCell = (attributeName) => {
            const cellTurmas = cell.getAttribute(attributeName).split(',').map(turma => turma.trim());
            const commonTurmas = cellTurmas.filter(turma => turmas.includes(turma));

            if (commonTurmas.length > 0) {
                cell.style.display = '';
                cell.setAttribute('colspan', commonTurmas.length.toString());
            }
        };

        // Procura pelos atributos 'data-group' ou 'data-turmas e processa as células
        if (cell.hasAttribute('data-group')) {
            processCell('data-group');
        } else if (cell.hasAttribute('data-turmas')) {
            processCell('data-turmas');
        } else {
            // Lida com células sem 'data-group' ou 'data-turmas'
            const cellIdMatches = cell.id.match(/turma_([^\_]+)/);
            if (cellIdMatches && turmas.some(turma => cell.id.includes(turma))) {
                cell.style.display = '';
            }
        }
    });
}

/**
 * Une células da tabela.
 * 
 * @returns {null} Não retorna qualquer valor.
 */
function mergeCells() {
    const cells = $("#table_vistas").find("td:not(:first-child):has(p)").toArray();

    cells.forEach(function (cell) {
        const colspan = parseInt(cell.getAttribute('colspan'));
        const originalColspan = parseInt(cell.getAttribute('data-originalcolspan'));

        if (originalColspan === colspan || !originalColspan) {
            return;
        }

        const aulaId = cell.getAttribute('data-aulaid');
        const nextSiblings = document.querySelectorAll("tbody td:not(:first-child)[data-aulaid='" + aulaId + "']");

        for (let i = 1; i < nextSiblings.length; i++) {
            nextSiblings[i].remove();
        }

        cell.setAttribute('colspan', originalColspan);
    })
}

/**
 * Separa células de uma tabela com base na lista de turmas.
 *
 * @param {Array} turmasLista - Lista de turmas cujas células devem ser separadas.
 * @returns {null} Não retorna qualquer valor.
 */
function unmergeCells(turmasLista) {
    const cells = $("#table_vistas").find("td:not(:first-child):has(p)").toArray();

    const turmasporturno = curso.anos[0].turmasPorTurno;

    cells.forEach(function (cell) {
        const colspan = parseInt(cell.getAttribute('colspan'));

        // If the cell is already unmerged or has no colspan, skip it
        if (colspan === 1 || !colspan) {
            return;
        }

        const cellId = cell.id;
        const cellTurma = cellId.split("_")[1];
        const turmaIndex = turmasLista.indexOf(cellTurma);

        for (let i = 1; i < colspan; i++) {
            const newCell = cell.cloneNode(true);
            const newCellTurma = turmasLista[turmaIndex + i];
            let newCellTurno = "turno";

            //Encontrar o turno a que pertence a célula
            for (const [key, arr] of Object.entries(turmasporturno)) {
                if (arr.includes(newCellTurma)) {
                    newCellTurno += key.toString();
                    break;
                }
            }

            const newCellId = cellId.split("_")[0] + '_' + newCellTurma + '_' + cellId.split("_")[2] + '_' + cellId.split("_")[3];
            newCell.setAttribute('id', newCellId);
            newCell.setAttribute('class', newCellTurno);
            newCell.setAttribute('colspan', 1);

            cell.parentNode.insertBefore(newCell, cell.nextSibling);
        }

        cell.setAttribute('colspan', '1');
    });
}

/**
 * Atualiza o colspan das células de header da tabela com base na visibilidade das colunas da tabela.
 * 
 * @returns {null} Não retorna qualquer valor.
 */
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

function updateDayDivisions() {
    const allTurmaCells = document.querySelectorAll("tbody [id*=turma_]");
    allTurmaCells.forEach(cell => {
        cell.classList.remove("last-turma");
        cell.classList.remove("first-turma");
    });

    const table = document.getElementById("table_vistas");
    const turmasRow = table.rows[1];
    const dayLength = Math.floor((turmasRow.cells.length - 1) / 6);
    let lastTurmaInDay;
    for (let i = dayLength; i >= 1; i--) {
        if (turmasRow.cells[i].style.display === '') {
            lastTurmaInDay = turmasRow.cells[i];
            break;
        }
    }

    const lastTurmaId = lastTurmaInDay.getAttribute("id").split('_')[1];
    const allPotentialCells = document.querySelectorAll(`tbody [id*="${lastTurmaId}"], tbody [data-turmas*="${lastTurmaId}"]`);

    const allLastTurmaCells = Array.from(allPotentialCells).filter(cell => {
        if (cell.hasAttribute('data-group')) {
            return cell.getAttribute('data-turmas').includes(lastTurmaId) && cell.getAttribute('data-group').includes(lastTurmaId);
        }
        return true;
    });
    allLastTurmaCells.forEach(cell => {
        cell.classList.add("last-turma");
    });
}

/**
 * Envia uma alteração de uma célula para a base de dados.
 * 
 * @param {HTMLElement} cell - A célula que contém a informação a ser submetida.
 * @returns {null} Não retorna qualquer valor.
 */
function submitToDatabase(cell) {
    // Obter id do projeto
    const url = window.location.pathname;
    const id = url.split('/').pop();

    const cellId = cell.id;
    const colspan = cell.getAttribute('colspan') ? parseInt(cell.getAttribute('colspan')) : 1;
    const rowspan = cell.getAttribute('rowspan') ? parseInt(cell.getAttribute('rowspan')) : 1;

    const turma = cellId.split('_')[1];
    const dia = cellId.split('_')[2];
    const day = switchDaytoNumber(dia);

    const horaInicio = parseInt(cellId.split('_')[3]);
    const aulaId = cell.getAttribute('data-aulaid');

    //Obter hora final
    let hora = horaInicio;
    let secondDigit;
    for (let i = 1; i <= rowspan; i++) {
        secondDigit = (hora / 10) % 10;
        if (secondDigit == 3) {
            hora += 70;
        } else {
            hora += 30;
        }
    }

    const turmasLista = curso.anos[0].turmas;
    const turmaIdsLista = [];

    const allAulas = document.querySelectorAll("tbody td:not(:first-child)[data-aulaid='" + aulaId + "']");

    if (allAulas.length > 1) { // Quando está apenas uma turma selecionada é preciso ir buscar o resto das aulas, no caso de ela ser uma teórica
        for (let i = 0; i < allAulas.length; i++) {
            const nextCell = allAulas[i];
            const nextCellId = nextCell.id;
            const nextCellTurma = nextCellId.split('_')[1];
            turmaIdsLista.push(nextCellTurma);
        }
    } else {
        const turmaIndex = turmasLista.indexOf(turma);
        for (let i = turmaIndex; i < turmaIndex + colspan; i++) {
            turmaIdsLista.push(turmasLista[i]);
        }
    }

    const uc = cell.querySelector('p.uc').id;
    const docentes = cell.querySelectorAll('p.docente');
    const salas = cell.querySelectorAll('p.sala');

    const docentesIds = [];
    for (let i = 0; i < docentes.length; i++) {
        docentesIds.push(docentes[i].id);
    }

    const salasIds = [];
    for (let i = 0; i < salas.length; i++) {
        salasIds.push(salas[i].id);
    }

    const formData = {
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

    // Faz o pedido AJAX
    $.ajax({
        data: JSON.stringify(formData),
        type: 'POST',
        url: "/editturnos/" + id + "/makechanges",

        headers: {
            'X-CSRFToken': formData.csrfmiddlewaretoken
        },

        // on success
        success: function (response) {
            const conflicts = response.conflicts
            writeConflicts(conflicts)
        },
        // on error
        error: function (response, status, error) {
            console.log(response.responseText)
        }
    });
}

/**
 * Troca o conteúdo e id de dois elementos HTML.
 * 
 * @param {HTMLElement} p1 - O primeiro elemento.
 * @param {HTMLElement} p2 - O segundo elemento.
 * @returns {null} Não retorna qualquer valor.
 */
function swapPartialCells(p1, p2) {
    // Obtém o conteúdo de p1
    const p1Content = p1.innerHTML;

    // Obtém o conteúdo de p2
    const p2Content = p2.innerHTML;

    // Troca o conteúdo de p1 e p2
    p1.innerHTML = p2Content;
    p2.innerHTML = p1Content;

    // Troca o id de p1 e p2
    const p1Id = p1.id;
    const p2Id = p2.id;
    p1.id = p2Id;
    p2.id = p1Id;
}

/**
 * Troca o conteúdo e atributos de duas células do horário.
 *
 * @param {HTMLElement} firstCell - A primeira célula.
 * @param {HTMLElement} secondCell - A segunda célula.
 */
function swapFullCells(firstCell, secondCell) {
    // Retrieve colspan and rowspan attributes, assigning default value 1 if not defined
    const colspanFirst = firstCell.getAttribute('colspan') ? parseInt(firstCell.getAttribute('colspan')) : 1;
    const rowspanFirst = firstCell.getAttribute('rowspan') ? parseInt(firstCell.getAttribute('rowspan')) : 1;

    const colspanSecond = secondCell.getAttribute('colspan') ? parseInt(secondCell.getAttribute('colspan')) : 1;
    const rowspanSecond = secondCell.getAttribute('rowspan') ? parseInt(secondCell.getAttribute('rowspan')) : 1;

    const class1 = firstCell.classList[0];
    const class2 = secondCell.classList[0];
    const id1 = firstCell.id;
    const id2 = secondCell.id;

    firstCell.setAttribute('class', class2);
    secondCell.setAttribute('class', class1);

    if (rowspanFirst == rowspanSecond && colspanFirst == colspanSecond) {
        createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst >= colspanSecond) {
        createCells(secondCell, colspanSecond - 1, rowspanSecond, 0);
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst <= colspanSecond) {
        if (rowspanFirst > rowspanSecond) {
            createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
            createCells(secondCell, colspanSecond - 1, rowspanSecond, 0);
        }
        else {
            createCells(firstCell, colspanFirst - 1, rowspanSecond, 0);
        }
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst >= colspanSecond) {
        if (colspanFirst > colspanSecond) {
            createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
            createCells(secondCell, colspanSecond - 1, rowspanSecond, 0);
        }
        else {
            createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
        }
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst <= colspanSecond) {
        createCells(firstCell, colspanFirst - 1, rowspanFirst, 0);
    }

    // Remove all div child elements from firstCell
    const firstDivChildren = firstCell.querySelectorAll('div');
    for (let i = 0; i < firstDivChildren.length; i++) {
        const divChild = firstDivChildren[i];
        firstCell.removeChild(divChild);
    }

    firstCell.setAttribute('id', id2);
    secondCell.setAttribute('id', id1);

    const parent1 = firstCell.parentNode;
    const sibling1 = firstCell.nextSibling;

    const parent2 = secondCell.parentNode;
    const sibling2 = secondCell.nextSibling;

    parent1.insertBefore(secondCell, sibling1);
    parent2.insertBefore(firstCell, sibling2);

    if (rowspanFirst == rowspanSecond && colspanFirst == colspanSecond) {
        deleteCells(secondCell, colspanSecond - 1, rowspanSecond - 1);
    }
    else if (rowspanFirst > rowspanSecond && colspanFirst > colspanSecond) {
        createCells(secondCell, colspanFirst - colspanSecond + 1, rowspanFirst, 1);
        deleteCells(firstCell, colspanFirst - colspanSecond, rowspanFirst - 1);
    }
    else if (rowspanFirst > rowspanSecond && colspanFirst <= colspanSecond) {
        if (colspanFirst < colspanSecond) {
            deleteCells(secondCell, colspanSecond - colspanFirst, rowspanSecond - 1);
            deleteCells(firstCell, colspanFirst - 1, rowspanFirst - 1);
        }
        else {
            createCells(secondCell, colspanSecond - colspanFirst + 1, rowspanFirst, 1);
            deleteCells(firstCell, colspanSecond - colspanFirst, rowspanFirst - 1);
        }
    }
    else if (rowspanFirst <= rowspanSecond && colspanFirst > colspanSecond) {
        if (rowspanFirst < rowspanSecond) {
            deleteCells(firstCell, colspanFirst - colspanSecond, rowspanFirst - 1);
            deleteCells(secondCell, colspanSecond - 1, rowspanSecond - 1);
        }
        else {
            createCells(secondCell, colspanFirst - colspanSecond + 1, rowspanSecond, 1);
            deleteCells(firstCell, colspanFirst - colspanSecond, rowspanSecond - 1);
        }
    }
    else if (rowspanFirst <= rowspanSecond && colspanFirst <= colspanSecond) {
        createCells(firstCell, colspanSecond - colspanFirst + 1, rowspanSecond, 1);
        deleteCells(secondCell, colspanSecond - colspanFirst, rowspanSecond - 1);
    }
}

/**
 * Verifica se duas células podem ser trocadas, com base nos seus atributos.
 * 
 * @param {HTMLElement} cell1 - A primeira célula.
 * @param {HTMLElement} cell2 - A segunda célula.
 * @returns {boolean} - Retorna true se as células podem ser trocadas. False, em caso contrário.
 */
function canSwap(cell1, cell2) {
    const colspanFirst = cell1.getAttribute('colspan') ? parseInt(cell1.getAttribute('colspan')) : 1;
    const originalcolspanFirst = cell1.getAttribute('data-originalcolspan') ? parseInt(cell1.getAttribute('data-originalcolspan')) : 1;
    const rowspanFirst = cell1.getAttribute('rowspan') ? parseInt(cell1.getAttribute('rowspan')) : 1;

    const colspanSecond = cell2.getAttribute('colspan') ? parseInt(cell2.getAttribute('colspan')) : 1;
    const originalcolspanSecond = cell2.getAttribute('data-originalcolspan') ? parseInt(cell2.getAttribute('data-originalcolspan')) : 1;
    const rowspanSecond = cell2.getAttribute('rowspan') ? parseInt(cell2.getAttribute('rowspan')) : 1;

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

    let swap;
    if (rowspanFirst == rowspanSecond && colspanFirst == colspanSecond) {
        swap = true;
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst >= colspanSecond) {
        swap = checkIfSwapPossible(cell2, cell1, colspanFirst - colspanSecond, rowspanFirst - 1);
    }
    else if (rowspanFirst >= rowspanSecond && colspanFirst < colspanSecond) {
        swap = checkIfSwapPossible(cell1, cell2, colspanSecond - colspanFirst, rowspanSecond - 1) && checkIfSwapPossible(cell2, cell1, colspanSecond - colspanFirst, rowspanFirst - 1);
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst >= colspanSecond) {
        swap = checkIfSwapPossible(cell1, cell2, colspanFirst - colspanSecond, rowspanSecond - 1) && checkIfSwapPossible(cell2, cell1, colspanFirst - colspanSecond, rowspanFirst - 1);
    }
    else if (rowspanFirst < rowspanSecond && colspanFirst < colspanSecond) {
        swap = checkIfSwapPossible(cell1, cell2, colspanSecond - colspanFirst, rowspanSecond - 1);
    }
    return swap;
}

/**
 * Verifica se uma troca é possível entre duas células do horário, com base na sua posição.
 * 
 * @param {HTMLElement} cell - A primeira célula.
 * @param {HTMLElement} cell2 - A segunda célula.
 * @param {number} cellsRight - Número de células à direita da primeira.
 * @param {number} cellsBottom - Número de células abaixo da primeira.
 * @returns {boolean} - Retorna true se as células podem ser trocadas. False, em caso contrário.
 */
function checkIfSwapPossible(cell, cell2, cellsRight, cellsBottom) {
    const turmasLista = curso.anos[0].turmas;

    let cellId = cell.id;
    const cellTurma = cellId.split("_")[1];
    const turmaIndex = turmasLista.indexOf(cellTurma);

    const colspan = cell.getAttribute('colspan') ? parseInt(cell.getAttribute('colspan')) : 1;
    const rowspan = cell.getAttribute('rowspan') ? parseInt(cell.getAttribute('rowspan')) : 1;

    for (let i = 0; i <= cellsBottom; i++) {
        count = cellsRight;
        while (count >= 0) {
            if (i < rowspan && count < colspan) {
                count--;
                continue;
            }
            const newCellTurma = turmasLista[turmaIndex + count];
            const newCellId = cellId.split("_")[0] + '_' + newCellTurma + '_' + cellId.split("_")[2] + '_' + cellId.split("_")[3];
            const newCell = document.querySelector("td#" + newCellId);

            if (!newCell)
                return false;

            if (newCellId == cell2.id)
                return true;

            let content = newCell.innerHTML;
            content = content.replace(/\s/g, "");

            if (content != '') {
                return false;
            }
            count--;
        }
        let hora = parseInt(cellId.split('_')[3]);
        secondDigit = (hora / 10) % 10;
        if (secondDigit == 3) {
            hora += 70;
        } else {
            hora += 30;
        }
        cellId = cellId.split('_')[0] + "_" + cellId.split('_')[1] + "_" + cellId.split('_')[2] + "_" + hora; //id da célula seguinte pertencente à mesma aula
    }
    return true;
}

// ------------------------------------------------------------------------------------------------
// Event listeners
// ------------------------------------------------------------------------------------------------

$(document).on('click', 'td:not(:first-child)', function (event) {
    const td = this;
    const targetElement = event.target;
    const turma = td.id.split('_')[1];

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
            const prevCell = document.querySelector("td:not(:first-child).selected");
            const idCellBefore = $(prevCell).attr('id');
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
    const uc = this;
    let siglaUC = uc.textContent;
    for (let i = 0; i < curso.ucs.length; i++) {
        let uc_sigla = curso.ucs[i].sigla;
        const indexOfParenthesis = uc_sigla.indexOf("(");
        if (indexOfParenthesis !== -1) {
            uc_sigla = uc_sigla.substring(0, indexOfParenthesis);
        }
        if (siglaUC == uc_sigla) {
            const name = curso.ucs[i].nome;
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
        }
    }
});

$(document).on('mouseleave', '#table_vistas td:not(:first-child):has(p) p.uc', function (event) {
    // MUDAR UCS
    const td = this;
    const nameUC = td.textContent;

    for (let i = 0; i < curso.ucs.length; i++) {
        const this_name = curso.ucs[i].nome;
        if (nameUC == this_name) {
            let siglaUC = curso.ucs[i].sigla;
            const indexOfParenthesis = siglaUC.indexOf("(");
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
    // MUDAR DOCENTES
    const siglaDocente = this.textContent;

    for (let i = 0; i < curso.docentes.length; i++) {
        const doc_sigla = curso.docentes[i].abreviacao;
        if (siglaDocente == doc_sigla) {
            if (!document.getElementById("tooltipcontainer")) {
                const name = curso.docentes[i].nome;
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
    const docente = this;
    const nomeDocente = this.textContent;

    for (let i = 0; i < curso.docentes.length; i++) {
        const nome_doc = curso.docentes[i].nome;
        if (nomeDocente == nome_doc) {
            const sigla = curso.docentes[i].abreviacao;
            docente.textContent = sigla;
            docente.style.whiteSpace = "nowrap";
        }
    }
    if (document.getElementById("tooltipcontainer")) {
        document.getElementById("tooltipcontainer").parentNode.removeChild(document.getElementById("tooltipcontainer"));
    }
});


$(document).on('click', 'td:not(:first-child) p', function (event) {
    // Previne que o evento se propague para o elemento td
    event.stopPropagation();
    const p = this;

    // 'Desseleciona' algum elemento td selecionado
    const selectedTD = $('td:not(:first-child).selected');
    if (selectedTD.length) {
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
        const cellClass = prevSelectedCell[0].classList;
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

function displayBlocosVermelhosTurma(turma, display) {
    if (!display) {
        const redCellsTd = document.querySelectorAll('td[style="background-color: red; opacity: 0.6;"]');
        const redCellsDiv = document.querySelectorAll('div[style="background-color: red; opacity: 0.6;"]');

        for (let i = 0; i < redCellsTd.length; i++) {
            redCellsTd[i].setAttribute("style", "");
        }

        for (let i = 0; i < redCellsDiv.length; i++) {
            redCellsDiv[i].setAttribute("style", "");
        }
        return;
    }

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
    for (var i = 0; i < blocosVermelhos.length; i++) {
        var bloco = blocosVermelhos[i];
        var dia = bloco.diaSemana;
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