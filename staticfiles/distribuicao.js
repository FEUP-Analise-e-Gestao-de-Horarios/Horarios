function fillTable() {
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
            if(tipo == "Anf")
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