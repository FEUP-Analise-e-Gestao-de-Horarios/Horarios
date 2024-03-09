/* setDocentesEditFormValues

called when a docente is selected
updates the initial values of the form to correspond with the selected docente
displays the form if it is hidden
*/
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

/* editDocenteForm submit

event: submit button pressed

retrieves the pre-changes id of the docente
retrieves the values inputed for the new id, name and abreviation
sends a Post Ajax request that checks if the new id is taken, if it is altered that is
if it is taken, an error message will be displayed under the id input
otherwise the changes are made and the page updated to reflect it
*/
$(document).ready(function () {
    $('#editDocenteForm').submit(function () {
        event.preventDefault()

        const errorContainer = $('#error-container-docente')
        
        //remove any error message
        errorContainer.empty()

        const url = window.location.pathname;
        const id = url.match(/\/(\d+)\//)[1];

        let idDocente = $('#numeroMecanografico').val()
        let nomeDocente = $('#nome').val().replace(/\s+$/, "")
        let siglaDocente = $('#abreviacao').val()
        const title = $('#title').text()
        const oldId = title.split('->')[0]

        const formData = {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
            idDocente: parseInt(idDocente, 10),
            nomeDocente: nomeDocente,
            siglaDocente: siglaDocente,
            oldId: parseInt(oldId, 10)
        };


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
                idDocente = response.idDocente
                nomeDocente = response.nomeDocente
                siglaDocente = response.siglaDocente


                let button = document.getElementById(parseInt(oldId, 10))
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

