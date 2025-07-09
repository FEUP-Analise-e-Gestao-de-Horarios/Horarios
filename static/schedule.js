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
        let aulas = uc.aulas; // FORMATO -> [Aula(id, horaInicial, duracao, diaSemana, isTeorica)]
        ucAnoBool = false;

        for (let j = 0; j < aulas.length; j++) {
            let aula = aulas[j];

            let turmas = aula.turmas; // FORMATO -> {ano: [codigoTurma]}
            if (!(ano in turmas)) { // Caso não tenha turmas do ano em que a tabela está
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
                let idString = "turma_" + group[0] + "_" + dia + "_" + hora;   // id da célula a que pertence a aula

                let cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); // célula a que pertence a aula
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

/**
 * Ordena as aulas de uma UC por número de turmas e depois por duração.
 * Este processo faz com que os blocos de UC sejam desenhados dos mais pequenos para os maiores.
 * 
 * @param {Object} uc - A UC com aulas a ordenar.
 * @return {null} Não retorna qualquer valor.
 */
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

/**
 * Determina o "peso" de uma UC, tendo em conta o número de turmas e a duração das suas aulas.
 * 
 * @param {Object} uc - A UC cujo peso deve ser determinado.  
 * @returns {number} Peso da UC.
 */
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

            let turmas = aula.turmas; // FORMATO -> {ano: [codigoTurma]}

            if (!(ano in turmas)) { // Caso não tenha turmas do ano em que a tabela está
                continue;
            }

            turmas = turmas[ano];
            let dia = aula.diaSemana.toLowerCase();
            let hora = aula.horaInicial;

            for (let k = 0; k < turmas.length; k++) {
                let turma = turmas[k];

                let idString = "turma_" + turma + "_" + dia + "_" + hora;

                let cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); // célula a que pertence a aula
                if (cell == null) {
                    continue;
                }

                const p_element = document.createElement("p");
                p_element.classList.add("docente");
                p_element.id = docente.numMecanografico;
                p_element.innerHTML = docente.abreviacao;
                p_element.setAttribute("data-bs-toggle", "popover");
                p_element.setAttribute("data-bs-title", docente.nome);

                const div_popover = document.createElement("div");
                div_popover.id = docente.numMecanografico;
                div_popover.style.display = "none";
                div_popover.innerHTML = docente.miniHorario;
                p_element.appendChild(div_popover);

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

            let turmas = aula.turmas; // FORMATO -> {ano: [codigoTurma]}
            if (!(ano in turmas)) { // Caso não tenha turmas do ano em que a tabela está
                continue;
            }

            turmas = turmas[ano];
            let dia = aula.diaSemana.toLowerCase();
            let hora = aula.horaInicial;

            for (let k = 0; k < turmas.length; k++) {
                let turma = turmas[k];

                const idString = "turma_" + turma + "_" + dia + "_" + hora;

                let cell = document.querySelector("tbody td:not(:first-child)[id='" + idString + "']"); // célula a que pertence a aula
                if (cell == null) {
                    continue;
                }

                const p_element = document.createElement("p");
                p_element.classList.add("sala");
                p_element.id = sala.numero;
                p_element.innerHTML = sala.numero;
                p_element.setAttribute("data-bs-toggle", "popover");
                p_element.setAttribute("data-bs-title", sala.numero);

                const div_popover = document.createElement("div");
                div_popover.id = sala.numero;
                div_popover.style.display = "none";
                div_popover.innerHTML = sala.miniHorario;
                p_element.appendChild(div_popover);

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

        cellId = cellId.split('_')[0] + "_" + cellId.split('_')[1] + "_" + cellId.split('_')[2] + "_" + hora; // id da célula seguinte pertencente à mesma aula
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
            idCell = idCellSplit[0] + "_" + idCellSplit[1] + "_" + idCellSplit[2] + "_" + hora; // id da célula seguinte pertencente à mesma aula
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
 * Faz o display de todas as aulas de uma dada turma.
 * 
 * @param {string} targetTurma A turma selecionada para visualização.
 * @return {null} Não retorna qualquer valor.
 */
function displayTurma(targetTurma) {
    const allTurmaCells = document.querySelectorAll("tbody td[id*=turma_], tbody th[id*=turma_]");
    allTurmaCells.forEach(cell => {
        cell.style.display = 'none';

        const displayCell = (cell) => {
            cell.style.display = '';
            cell.setAttribute('colspan', '1');
        }

        if (cell.hasAttribute('data-group')) {
            if (cell.getAttribute('data-group').includes(targetTurma)) {
                displayCell(cell);
            }
        } else if (cell.hasAttribute('data-turmas')) {
            if (cell.getAttribute('data-turmas').includes(targetTurma)) {
                displayCell(cell);
            }
        } else {
            if (cell.id.includes(targetTurma)) {
                displayCell(cell);
            }
        }
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

    // Coloca em children apenas os elementos que estão visíveis
    for (let i = 0; i < columns.children.length; i++) {
        const child = columns.children[i];
        if (child.style.display === '') {
            children.push(child);
        }
    }

    const numColumns = children.length - 1; // nº de colunas visíveis
    const colspanValue = Math.floor(numColumns / 6);

    headerRow.querySelectorAll("th").forEach((th, index) => {
        if (index === 0) {
            th.setAttribute("colspan", 1);
        } else {
            th.setAttribute("colspan", colspanValue);
        }
    });
}

/**
 * Atualiza a posição da linha de divisão entre dias no horário,
 * de acordo com o layout.
 * 
 * @returns {null} Não retorna qualquer valor.
 */
function updateDayDivisions() {
    const allTurmaCells = document.querySelectorAll("tbody [id*=turma_]");
    allTurmaCells.forEach(cell => {
        cell.classList.remove("last-turma");
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
    const allPotentialCells = document.querySelectorAll(`tbody td[id*="${lastTurmaId}"], tbody [data-turmas*="${lastTurmaId}"]`);

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
 * Inicializa os popovers dos docentes e salas que contêm um
 * mini-horário com as disponibilidades dessas entidades.
 * 
 * @returns {null} Não retorna qualquer valor.
 */
function enablePopovers() {
    const docentesP = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popovers = [...docentesP].map(p => new bootstrap.Popover(p,
        {
            trigger: 'hover focus',
            html: true,
            content: p.firstElementChild.innerHTML
        }
    ));
}

/**
 * Atualiza o popover de um elemento <p> de um docente, em todas as células aplicáveis.
 * 
 * @param {string} idDocente Número mecanográfico do docente.
 * @returns {null} Não retorna qualquer valor.
 */
function updatePopoverDocente(idDocente) {
    const docenteP = document.querySelectorAll(`p[id="${idDocente}"]`);
    fetchDocenteMiniHorario(idDocente, projId).then(response => {
        docenteP.forEach(p => {
            p.firstElementChild.innerHTML = response.docenteHorario;
            const popover = bootstrap.Popover.getInstance(p);
            popover.setContent({
                '.popover-header': p.getAttribute("data-bs-title"),
                '.popover-body': response.docenteHorario
            });
        });
    });
}

/**
 * Atualiza o popover de um elemento <p> de uma sala, em todas as células aplicáveis.
 * 
 * @param {string} idSala 
 * @returns {null} Não retorna qualquer valor.
 */
function updatePopoverSala(idSala) {
    const salaP = document.querySelectorAll(`p[id="${idSala}"]`);
    fetchSalaMiniHorario(idSala, projId).then(response => {
        salaP.forEach(p => {
            p.firstElementChild.innerHTML = response.salaHorario;
            const popover = bootstrap.Popover.getInstance(p);
            popover.setContent({
                '.popover-header': p.getAttribute("data-bs-title"),
                '.popover-body': response.salaHorario
            });
        });
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

    // Obter hora final
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
    }).then(_ => {
        docentes.forEach(docente => {
            updatePopoverDocente(docente.id);
        });

        salas.forEach(sala => {
            updatePopoverSala(sala.id);
        });
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
    const firstDivChildren = firstCell.querySelectorAll(':scope > div');
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
async function canSwap(cell1, cell2) {
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

    if (swap) {
        const aulaId = cell1.getAttribute("data-aulaid");
        const projectNumber = $('script[data-proj-id]').data('projId');
    
        const response = await fetch(`/getaulaparalelosimultanea?projId=${projectNumber}&aulaId=${aulaId}`);
        const data = await response.json();

            
        if (data.paralelo) {
            const opcao = await new Promise(resolve => abrirPopupParalelo(resolve));
            if (opcao === 'cancelar')
                swap = false;  
        }
        if (data.simultanea) {
            const opcao = await new Promise(resolve => abrirPopupSimultanea(resolve));
            if (opcao === 'cancelar')
                swap = false;
        }
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
        cellId = cellId.split('_')[0] + "_" + cellId.split('_')[1] + "_" + cellId.split('_')[2] + "_" + hora; // id da célula seguinte pertencente à mesma aula
    }
    return true;
}

// ------------------------------------------------------------------------------------------------
// Event listeners
// ------------------------------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', function () {
    const myDefaultAllowList = bootstrap.Tooltip.Default.allowList;
    myDefaultAllowList.table = [];
    myDefaultAllowList.thead = [];
    myDefaultAllowList.tbody = [];
    myDefaultAllowList.tr = [];
    myDefaultAllowList.th = [];
    myDefaultAllowList.td = [];
});

$(document).on('click', 'td:not(:first-child)', async function (event) {
    const td = this;
    const targetElement = event.target;
    const turma = td.id.split('_')[1];
    const projectNumber = $('script[data-proj-id]').data('projId');

    // Check if the target element is the td itself or a descendant of the td
    if (targetElement === td || $.contains(td, targetElement)) {
        // Unselect any selected p element
        const selectedP = $('td:not(:first-child) p.selected');
        if (selectedP.length) {
            showEditBarOptions(false);
            selectedP.removeClass('selected');
            displayBlocosVermelhosGlobal(selectedP.attr('class'), selectedP.attr('id'), false);
        }

        // Caso se tente selecionar uma célula que já estava selecionada
        if ($(td).hasClass('selected')) {
            showEditBarOptions(false);
            $(td).removeClass('selected');
            clearHighlight();

            // Remove borders from p elements
            $(td).find('p').css('border', '');
            return;
        }

        const prevSelectedCell = $('td:not(:first-child).selected');
        // Caso já exista uma célula selecionada, então é preciso trocá-las
        if (prevSelectedCell.length === 1) {
            const prevCell = document.querySelector("td:not(:first-child).selected");
            const idCellBefore = $(prevCell).attr('id');

            try {
                if (await canSwap(prevCell, td)) {
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

        // Remove class from all other td
        document.querySelectorAll("td:not(:first-child)").forEach(td => {
            showEditBarOptions(false);
        });

        // Unselect da primeira célula selecionada
        $('td:not(:first-child)').removeClass('selected');

        if (prevSelectedCell.length == 0) {
            // Select da primeira célula selecionada
            $(td).addClass('selected');
            if ($(td).has('p').length > 0) {

                const docenteElement = $(td).find('p.docente');
                const salaElement = $(td).find('p.sala');
                if (docenteElement.length > 0 && salaElement.length > 0) {
                    const docenteId = docenteElement.attr('id');
                    const numeroSala = salaElement.attr('id');
                    clearHighlight();  // Limpa os destaques antes de adicionar novos
                    displayTodosConflitos(docenteId, numeroSala, true); // Chama a função para destacar os conflitos duplos

                    // Add borders only to the specific cell
                    docenteElement.css('border', '2px solid yellow');
                    salaElement.css('border', '2px solid orange');
                } else {
                    if (docenteElement.length > 0) {
                        const docenteId = docenteElement.attr('id');
                        console.log('Docente selecionado com id:', docenteId);
                        clearHighlight();  // Limpa os destaques antes de adicionar novos
                        displayBlocosAmarelos(docenteId, true);  // Chama a função para destacar os blocos amarelos
                        docenteElement.css('border', '2px solid yellow');  // Add border
                    }
                    if (salaElement.length > 0) {
                        const numeroSala = salaElement.attr('id');
                        console.log('Sala selecionada com id:', numeroSala);
                        clearHighlight();  // Limpa os destaques antes de adicionar novos
                        displayBlocosLaranjas(numeroSala, true);  // Chama a função para destacar os blocos laranja
                        salaElement.css('border', '2px solid orange');  // Add border
                    }
                }
            }
        }

        if (td.children.length > 0) {
            showEditBarOptions(true);
            selectedCellSelectSideBar(targetElement, false);
        } else {
            showEditBarOptions(false);
        }
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

$(document).on('click', 'td:not(:first-child) p', function (event) {
    // Previne que o evento se propague para o elemento td
    event.stopPropagation();
    const p = this;
    const projectNumber = $('script[data-proj-id]').data('projId');
    const elementoId = $(p).attr('id');
    const className = $(p).attr('class');

    if (className.includes('docente')) {
        console.log('Docente selecionado com id:', elementoId, 'projectNumber:', projectNumber);
        clearHighlight();  // Limpa os destaques amarelos antes de adicionar novos
        displayBlocosAmarelos(elementoId, true);  // Chama a função para destacar os blocos amarelos
    } else if (className.includes('sala')) {
        const numeroSala = elementoId;
        console.log('Sala selecionada com id:', numeroSala, 'projectNumber:', projectNumber);
        clearHighlight();  // Limpa os destaques laranja antes de adicionar novos
        displayBlocosLaranjas(numeroSala, true);  // Chama a função para destacar os blocos laranja
    }

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

/**
 * Limpa os destaques (background color e opacity) das células.
 */
function clearHighlight() {
    const highlightedCells = document.querySelectorAll('td[style*="background-color: yellow"], td[style*="opacity: 0.6"]');
    highlightedCells.forEach(cell => {
        cell.style.backgroundColor = "";
        cell.style.opacity = "";
    });
}

/**
 * Mostra ou oculta blocos vermelhos para um elemento global (docente ou sala).
 * 
 * @param {string} className - A classe do elemento (docente ou sala).
 * @param {string} id - O ID do elemento.
 * @param {boolean} display - Determina se os blocos vermelhos devem ser exibidos ou ocultados.
 */
function displayBlocosVermelhosGlobal(className, id, display) {
    var blocosVermelhos;
    if (className === 'docente selected' || className === 'docente') {
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

        // Chama a função para destacar os blocos amarelos
        displayBlocosAmarelos(id, display);
    } else if (className === 'sala selected' || className === 'sala') {
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

        // Chama a função para destacar os blocos laranja
        displayBlocosLaranjas(id, display);
    }
}

/**
 * Mostra ou oculta blocos vermelhos para um conjunto de blocos.
 * 
 * @param {Array} blocosVermelhos - Array de blocos a serem destacados.
 * @param {boolean} display - Determina se os blocos vermelhos devem ser exibidos ou ocultados.
 * @param {string} turma - A turma alvo.
 */
function displayBlocosVermelhos(blocosVermelhos, display, turma) {
    for (var i = 0; i < blocosVermelhos.length; i++) {
        var bloco = blocosVermelhos[i];
        var dia = bloco.diaSemana;
        var substring = dia.toLowerCase() + "_" + bloco.hora;
        var targetElements, targetElements2;

        if (turma == 'any') {
            // Blocos vermelhos que estarão em células já preenchidas
            var selector = "div[id*=" + substring + "]";
            targetElements = document.querySelectorAll(selector);

            // Blocos vermelhos que estarão em células vazias
            var selector2 = "td:not(:has(div))[id*=" + substring + "]";
            targetElements2 = $(selector2);
        }
        else {
            // Blocos vermelhos que estarão em células já preenchidas
            var selector = 'div[id*="' + substring + '"]:has([id*="' + turma + '"])';
            targetElements = $(selector);

            // Blocos vermelhos que estarão em células vazias
            var selector2 = 'td:not(:has(div))[id*="' + substring + '"][id*="' + turma + '"]';
            targetElements2 = $(selector2);
        }

        // Blocos vermelhos que estão em células já preenchidas
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

        // Blocos vermelhos que estão em células vazias
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

/**
 * Mostra ou oculta blocos amarelos para um docente específico.
 * 
 * @param {string} docenteId - O ID do docente.
 * @param {boolean} display - Determina se os blocos amarelos devem ser exibidos ou ocultados.
 */
function displayBlocosAmarelos(docenteId, display) {
    const projectNumber = $('script[data-proj-id]').data('projId');

    fetchDocenteHorario(docenteId, projectNumber).then(aulas => {
        aulas.forEach(aula => {
            const dia = aula.diaSemana.toLowerCase();
            let hora = aula.horaInicial;
            const numBlocos = aula.duracao; // Duração em número de blocos de 30 minutos

            // Cria um array de horários baseados na duração
            const horarios = [];
            for (let i = 0; i < numBlocos; i++) {
                horarios.push(hora);
                hora += 30;
                if (hora % 100 >= 60) {
                    hora = hora + 40; // Corrige para o próximo horário válido (pula de 1430 para 1500, por exemplo)
                }
            }

            // Destaca todos os horários no array
            horarios.forEach(hora => {
                const horas = Math.floor(hora / 100).toString().padStart(2, '0');
                const minutos = (hora % 100).toString().padStart(2, '0');
                const idString = `${dia}_${horas}${minutos}`;

                const cells = document.querySelectorAll(`td[id*="${idString}"]:not(:has(p))`);

                cells.forEach(cell => {
                    if (display) {
                        cell.style.backgroundColor = "yellow";
                        cell.style.opacity = 0.6;
                    } else {
                        cell.style.backgroundColor = "";
                        cell.style.opacity = "";
                    }
                });
            });
        });
    }).catch(error => {
        console.error('Erro ao buscar horários do docente:', error);
    });
}

/**
 * Mostra ou oculta blocos laranja para uma sala específica.
 * 
 * @param {string} salaId - O ID da sala.
 * @param {boolean} display - Determina se os blocos laranja devem ser exibidos ou ocultados.
 */
function displayBlocosLaranjas(salaId, display) {
    const projectNumber = $('script[data-proj-id]').data('projId');

    fetchSalaHorario(salaId, projectNumber).then(aulas => {
        aulas.forEach(aula => {
            const dia = aula.diaSemana.toLowerCase();
            let hora = aula.horaInicial;
            const numBlocos = aula.duracao; // Duração em número de blocos de 30 minutos

            // Cria um array de horários baseados na duração
            const horarios = [];
            for (let i = 0; i < numBlocos; i++) {
                horarios.push(hora);
                hora += 30;
                if (hora % 100 >= 60) {
                    hora = hora + 40; // Corrige para o próximo horário válido (pula de 1430 para 1500, por exemplo)
                }
            }

            // Destaca todos os horários no array
            horarios.forEach(hora => {
                const horas = Math.floor(hora / 100).toString().padStart(2, '0');
                const minutos = (hora % 100).toString().padStart(2, '0');
                const idString = `${dia}_${horas}${minutos}`;

                const cells = document.querySelectorAll(`td[id*="${idString}"]:not(:has(p))`);

                cells.forEach(cell => {
                    if (display) {
                        cell.style.backgroundColor = "orange";
                        cell.style.opacity = 0.6;
                    } else {
                        cell.style.backgroundColor = "";
                        cell.style.opacity = "";
                    }
                });
            });
        });
    }).catch(error => {
        console.error('Erro ao buscar horários da sala:', error);
    });
}

/**
 * Mostra ou oculta blocos cinza que representam conflitos duplos (docente e sala).
 * 
 * @param {string} docenteId - O ID do docente.
 * @param {string} numeroSala - O número da sala.
 * @param {boolean} display - Determina se os blocos de conflitos duplos devem ser exibidos ou ocultados.
 */
function displayBlocosConflitosDuplos(docenteId, numeroSala, display) {
    const projectNumber = $('script[data-proj-id]').data('projId');

    Promise.all([fetchDocenteHorario(docenteId, projectNumber), fetchSalaHorario(numeroSala, projectNumber)])
        .then(([aulasDocente, aulasSala]) => {
            const horariosDocente = [];
            const horariosSala = [];

            aulasDocente.forEach(aula => {
                let hora = aula.horaInicial;
                const numBlocos = aula.duracao;
                for (let i = 0; i < numBlocos; i++) {
                    horariosDocente.push(`${aula.diaSemana.toLowerCase()}_${hora}`);
                    hora += 30;
                    if (hora % 100 >= 60) {
                        hora = hora + 40;
                    }
                }
            });

            aulasSala.forEach(aula => {
                let hora = aula.horaInicial;
                const numBlocos = aula.duracao;
                for (let i = 0; i < numBlocos; i++) {
                    horariosSala.push(`${aula.diaSemana.toLowerCase()}_${hora}`);
                    hora += 30;
                    if (hora % 100 >= 60) {
                        hora = hora + 40;
                    }
                }
            });

            const conflitosDuplos = horariosDocente.filter(horario => horariosSala.includes(horario));

            conflitosDuplos.forEach(horario => {
                const cells = document.querySelectorAll(`td[id*="${horario}"]:not(:has(p))`);
                cells.forEach(cell => {
                    if (display) {
                        cell.style.backgroundColor = "grey";
                        cell.style.opacity = 0.6;
                    } else {
                        cell.style.backgroundColor = "";
                        cell.style.opacity = "";
                    }
                });
            });
        })
        .catch(error => {
            console.error('Erro ao buscar horários:', error);
        });
}

/**
 * Mostra ou oculta todos os conflitos (docente e sala).
 * 
 * @param {string} docenteId - O ID do docente.
 * @param {string} numeroSala - O número da sala.
 * @param {boolean} display - Determina se os conflitos devem ser exibidos ou ocultados.
 */
function displayTodosConflitos(docenteId, numeroSala, display) {
    const projectNumber = $('script[data-proj-id]').data('projId');

    // Destaque de conflitos de docente
    displayBlocosAmarelos(docenteId, display);

    // Destaque de conflitos de sala
    displayBlocosLaranjas(numeroSala, display);

    // Destaque de conflitos duplos (docente e sala)
    displayBlocosConflitosDuplos(docenteId, numeroSala, display);
}

/**
 * Faz uma requisição para buscar o horário de um docente.
 * 
 * @param {string} docenteId - O ID do docente.
 * @param {number} projectNumber - O número do projeto.
 * @returns {Promise} - Promessa que retorna o horário do docente.
 */
function fetchDocenteHorario(docenteId, projectNumber) {
    console.log(`Fetching schedule for docenteId: ${docenteId}, projectNumber: ${projectNumber}`);
    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/getdocentehorario/',
            method: 'GET',
            data: { docenteId: docenteId, projectNumber: projectNumber },
            success: function (data) {
                console.log('Horário recebido:', data);
                resolve(data);
            },
            error: function (error) {
                console.error('Erro ao buscar horário do docente:', error);
                reject(error);
            }
        });
    });
}

/**
 * Faz uma requisição para buscar o horário de uma sala.
 * 
 * @param {string} salaId - O ID da sala.
 * @param {number} projectNumber - O número do projeto.
 * @returns {Promise} - Promessa que retorna o horário da sala.
 */
function fetchSalaHorario(salaId, projectNumber) {
    console.log(`Fetching schedule for sala: ${salaId}, projectNumber: ${projectNumber}`);
    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/getsalahorario/',
            method: 'GET',
            data: { salaId: salaId, projectNumber: projectNumber },
            success: function (data) {
                console.log('Horário da sala recebido:', data);
                resolve(data);
            },
            error: function (error) {
                console.error('Erro ao buscar horário da sala:', error);
                reject(error);
            }
        });
    });
}

/**
 * Obtém o mini-horário HTML de um docente do servidor.
 * 
 * @param {string} docenteId Número mecanográfico do docente.
 * @param {int} projectNumber Número do projeto.
 * @returns {Promise} O horário HTML do docente, ou um erro.
 */
function fetchDocenteMiniHorario(docenteId, projectNumber) {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/getdocenteminihorario',
            method: "GET",
            data: {
                docenteId: docenteId,
                projectNumber: projectNumber
            },
            success: function (data) {
                resolve(data);
            },
            error: function (error) {
                console.error("Erro ao buscar mini-horário do docente:", error);
                reject(error);
            }
        });
    });
}

/**
 * Obtém o mini-horário HTML de uma sala do servidor.
 * 
 * @param {string} salaId Identificador da sala.
 * @param {int} projectNumber Número do projeto
 * @returns {Promise} O horário HTML da sala, ou um erro.
 */
function fetchSalaMiniHorario(salaId, projectNumber) {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/getsalaminihorario',
            method: 'GET',
            data: {
                salaId: salaId,
                projectNumber: projectNumber
            },
            success: function (data) {
                resolve(data);
            },
            error: function (error) {
                console.error("Erro ao buscar mini-horário da sala:", error);
                reject(error);
            }
        });
    });
}
