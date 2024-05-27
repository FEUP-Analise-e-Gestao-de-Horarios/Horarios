/**
 * Preenche a tabela da distribuição de tipos de aula em cada turmo,
 * localizada no fundo da página do horário
 * @return {void} Não retorna um resultado
 */
function fillTable() {
    const days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"];
    const tableBody = document.querySelector("#table_Distribution tbody");
    const tableHeader = document.querySelector("#table_Distribution thead tr");

    tableBody.innerHTML = "";
    tableHeader.innerHTML = '<th>Tipo</th><th>UC</th>';

    let countUCs = 0;
    let addTurnoHeader = true;

    // Obtém o número máximo de turnos das UCs para determinar o tamanho da tabela
    let maxTurnos = getMaxTurnos(Object.entries(ucsDistribuicao));

    // Loop principal para lidar com as distribuições dos tipos
    Object.entries(ucsDistribuicao).forEach(([sigla, distribuicao]) => {
        const ucColor = `style='background-color: ${window.colorDictionary[countUCs][0]};'`;
        const ucElem = `<td ${ucColor}>${sigla.slice(0, sigla.indexOf("("))}</td>`;
        countUCs++;

        Object.keys(distribuicao).forEach(tipo => {
            if (tipo === "Anf" || tipo === 'Desconhecido') return;

            const tipoElem = `<td>${tipo}</td>`;
            let fullLine = `<tr>${tipoElem}${ucElem}`;

            for (let i = 1; i <= maxTurnos; i++) {
                if (addTurnoHeader) {
                    createHeaderTurno();
                }

                // Se o turno não existir, cria uma célula vazia
                if (!distribuicao[tipo][i]) {
                    fullLine += days.map(() => createEmptyCell(window.colorDictionary[29][1])).join('') +
                        createEmptyCell(window.colorDictionary[29][1]);
                    continue;
                }

                // Adiciona as células de cada dia à linha da UC para este tipo
                const cells = createCellsForDays(distribuicao[tipo][i]);
                fullLine += cells;
            }

            // Adiciona a linha completa à tabela
            addTurnoHeader = false;
            tableBody.innerHTML += fullLine + "</tr>";
        });
    });
}

/**
 * Função auxiliar para obter o número máximo de turnos numa lista de UCs
 * @param {Array} ucs - Um array de objetos UC, contendo a sigla e a distribuição
 * dos tipos de aulas
 * @returns {number} O número máximo de turnos na lista
 */
function getMaxTurnos(ucs) {
    return ucs.reduce((maxTurnos, [_, distribuicao]) => {
        for (let tipo in distribuicao) {
            const numTurnos = Object.keys(distribuicao[tipo]).length;
            if (numTurnos > maxTurnos) {
                maxTurnos = numTurnos;
            }
        }
        return maxTurnos;
    }, 0);
}

/**
 * Função auxiliar que cria o header para um turno
 * @return { void } Não retorna um resultado
 */
function createHeaderTurno() {
    const headerTurno = days.map(day => `<th colspan='1' class='${day.toLowerCase()}'>${day}</th>`).join('') +
        "<th colspan='1' class='last-column'>Soma</th>";
    tableHeader.innerHTML += headerTurno;
}


/**
 * Cria uma célula vazia com uma dada cor
 * @param { number[] } backgroundColor - Cor da célula vazia
 * @returns { String } String que representa o elemento HTML da célula
 */
function createEmptyCell(backgroundColor) {
    return `<td style='background-color: ${backgroundColor};'></td>`;
}

/**
 * Cria células para uma UC específica e respetiva distribuição
 * @param { Object } distribuicaoTurno - Objeto que representa um tipo de aulas da UC com a distribuição pelos dias
 * @returns { String } String que representa a linha da tabela para esta UC
 */
function createCellsForDays(distribuicaoTurno) {
    let cells = "";
    let sum = 0;

    days.forEach(day => {
        const count = distribuicaoTurno[day] || 0;
        sum += count;
        cells += `<td>${count}</td>`;
    });

    cells += `<td class='last-column'>${sum}</td>`;
    return cells;
}