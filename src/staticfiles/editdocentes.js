function setDocentesEditFormValues(button){
    const docenteId = button.id;
    const buttonText = button.textContent;
    const abreviacao = buttonText.split(" -- ")[0].trim();
    const nome = buttonText.split(" -- ")[1].replace(/\n/g, '');

    const hiddenPlaceHolder = document.querySelector("#edit-form-hidden-div")
    const h3 = hiddenPlaceHolder.querySelector('h3')
    const form = document.querySelector("#editDocenteForm")

    if(form.classList.contains('hidden')){
        hiddenPlaceHolder.classList.add('hidden')
        h3.classList.add('hidden')
        form.classList.remove('hidden')
    }

    const h1 = form.querySelector('h1')
    h1.textContent = docenteId + " -> " + abreviacao + " -> " + nome

    $('#oldId').val(docenteId)
    $('#numeroMecanografico').val(docenteId)
    $('#nome').val(nome)
    $('#abreviacao').val(abreviacao)
}

$(document).ready(function () {
    $('#editDocenteForm').submit(function () {
        event.preventDefault()

        const errorContainer = $('#error-container-docente')
        
        //remove any error message
        errorContainer.empty()

        const url = window.location.pathname;
        const id = url.match(/\/(\d+)\//)[1];
        console.log('id:', id)

        const idDocente = $('#numeroMecanografico').val()
        const nomeDocente = $('#nome').val().replace(/\s+$/, "")
        const siglaDocente = $('#abreviacao').val()
        const title = $('#title').text()
        const oldId = title.split('->')[0]

        const formData = {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
            idDocente: parseInt(idDocente, 10),
            nomeDocente: nomeDocente,
            siglaDocente: siglaDocente,
            oldId: parseInt(oldId, 10)
        };

        console.log(formData)

        // create an AJAX call
        $.ajax({
            data: JSON.stringify(formData), // get the form data
            type: $(this).attr('method'), // GET or POST
            url: "/editturnos/"+id+"/editDocentes/makeChange/",

            headers:{
                'X-CSRFToken': formData.csrfmiddlewaretoken
            },

            // on success
            success: function (response) {
                let button = document.getElementById(parseInt(oldId, 10))
                console.log(button)
                button.id = idDocente
                button.textContent = siglaDocente+' -- '+nomeDocente
                const newbutton = document.getElementById(parseInt(idDocente, 10))
                setDocentesEditFormValues(newbutton)
            },
            // on error
            error: function (response, status, error) {
                if(response.status == 409){
                    const errorMessage = $('<p class="text-danger">Número Mecanográfico Inválido ou Repetido!</p>')
                    errorContainer.append(errorMessage)
                }else{
                    console.log(response.responseText)
                    alert(response.responseText)
                }
            }
        });
        return false;
    });
})

function returnToPrevious(){
    window.history.back();
}

