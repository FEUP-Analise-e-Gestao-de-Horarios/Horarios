function fillTable() {
    const colorDictionary = {
        0: ["#FFDABF", "#FFEED9"],   // Light Orange
        1: ["#EAEAB5", "#F4F4CE"],  // Light Olive
        2: ["#CCFFCC", "#E6FFE6"],   // Light Green
        3: ["#FFFFCC", "#FFFFE6"],   // Light Yellow
        4: ["#fcdcdc", "#f2e1e1"],  // Misty Rose
        5: ["#FFCCFF", "#FFE6FF"],   // Light Magenta
        6: ["#FFD1D9", "#FFE0E8"],   // Light Pink
        7: ["#E7CEFF", "#F0DFFF"],   // Light Purple
        8: ["#BDFFBD", "#D9FFD9"],   // Light Dark Green
        9: ["#BDBDFF", "#D9D9FF"],   // Light Navy
        10: ["#FFBDBD", "#FFD9D9"],  // Light Maroon
        11: ["#BDFEFF", "#D9FFFF"],  // Light Teal
        12: ["#D9D9D9", "#ECECEC"],  // Light Gray
        13: ["#FFEBC6", "#FFF5E0"],  // Light Apricot
        14: ["#DEFFB3", "#EFFFCC"],  // Light Lime
        15: ["#FFFCE6", "#FFFFF0"],  // Lemon Chiffon
        16: ["#FFD1D9", "#FFE0E8"],  // Light Pink
        17: ["#C6E6E9", "#D6EBED"],  // Light Powder Blue
        18: ["#E6D9E6", "#F0EAF0"],  // Light Thistle
        19: ["#FFEC96", "#FFF5CC"],  // Light Gold
        20: ["#FFEED9", "#FFF7E6"],  // Light Bisque
        21: ["#CCCCFF", "#E6E6FF"],  // Light Blue
        22: ["#E0FFFF", "#F0FFFF"],  // Cyan / Aqua
        23: ["#B8F4D8", "#CCFCE3"],  // Aquamarine
        24: ["#FFF8E7", "#FFFDF0"],  // Light Blanched Almond
        25: ["#B0E0F8", "#CCE8FF"],  // Light Sky Blue
        26: ["#F0C8F0", "#F7DFF7"],  // Plum
        27: ["#FFC4B3", "#FFD9CA"],  // Light Salmon
        28: ["#5CD8B2", "#8CF5CB"],  // Light Sea Green
        29: ["#A3AEB9", "#C1CDD3"],  // Light Slate Gray
        30: ["#F0FFFF", "#F5FFFF"],  // Light Cyan
        31: ["#FFD1D9", "#FFE0E8"],   // Light Pink
        32: ["#F0F0FF", "#F5F5FF"],  // Lavender
        33: ["#FFF5FB", "#FFFAFF"],  // Lavender Blush
        34: ["#CCFFFF", "#E6FFFF"],  // Light Cyan
        35: ["#B3F586", "#D2FFA0"],  // Lawn Green
        36: ["#C1F0FF", "#D6F7FF"],  // Light Sky Blue
        37: ["#C6E6F5", "#D6ECF7"],  // Light Blue
        38: ["#FAB0B0", "#FFCCCC"],  // Light Coral
        39: ["#FAB0B0", "#FFCCCC"]  // Light Coral
    };
    var tableBody = document.querySelector("#table_Distribution tbody");
    var tableHeader = document.querySelector("#table_Distribution thead tr");
    var headerTurno = '<th colspan="1" class = "segunda" >Segunda</th>' +
                        '<th colspan="1" class = "terça" >Terça</th>' +
                        '<th colspan="1" class = "quarta" >Quarta</th>' +
                        '<th colspan="1" class = "quinta" >Quinta</th>' +
                        '<th colspan="1" class = "sexta" >Sexta</th>' +
                        '<th>Soma</th>';
    tableBody.innerHTML = "";
    tableHeader.innerHTML = '<th>Tipo</th>' + '<th>UC</th>';

    var countUCs = 0;
    var addTurnoHeader = true;
    for(var [sigla, distribuicao] of Object.entries(ucsDistribuicao)){
        //FORMATO -> {tipo_sala: {numero_turno: {dia_semana: num_aulas}}}

        var uc_color =  " style='background-color: " + colorDictionary[countUCs][0] + ";'";
        var uc_elem = "<td" + uc_color + ">"+ sigla.slice(0, sigla.indexOf("(")) + "</td>";

        countUCs+=1;

        for(var tipo in distribuicao) {
            var distruibuicao_tipo = distribuicao[tipo];
            if(tipo == "Anf" || tipo=='Desconhecido')
                continue;

            var tipo_elem = "<td>"+ tipo + "</td>";
            var full_line = "<tr>" + tipo_elem + uc_elem;

            for(var turno in distruibuicao_tipo) {
                var distruibuicao_turno = distruibuicao_tipo[turno];

                if(addTurnoHeader == true) {
                    tableHeader.innerHTML += headerTurno;
                }

                var count_days_elem = "";
                var sum = 0;

                var days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"];
                for(let j=0; j<days.length; j++) {
                    var count = 0;
                    if(days[j] in distruibuicao_turno) {
                        count = distruibuicao_turno[days[j]];
                    }
                    sum += count;
                    count_days_elem += "<td>"+ count + "</td>";
                }

                var sum_elem = "<td>"+ sum + "</td>";
                full_line += count_days_elem + sum_elem;    
            }
            addTurnoHeader = false;
            tableBody.innerHTML += full_line + "</tr>";
        }
    }
}