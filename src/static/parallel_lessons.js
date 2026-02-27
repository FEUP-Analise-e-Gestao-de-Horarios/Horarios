function toggleCurso(button) {
    const curso = button.dataset.curso;
    const isActive = button.classList.toggle('active');

    document.querySelectorAll(`.curso-wrapper[data-curso="${curso}"]`).forEach(el => {
        el.style.display = isActive ? 'block' : 'none';
    });
}

function toggleUC(header) {
    const container = header.nextElementSibling;
    const icon = header.querySelector(".toggle-icon");
    const isHidden = window.getComputedStyle(container).display === "none";
    container.style.display = isHidden ? "block" : "none";
    icon.textContent = isHidden ? "▾" : "▸";
}

// dentro dos grupos de aulas ao mesmo tempo, se uma aula tiver sido selecionada numa checkbox então desativa essa opção nas outras checkboxes
function atualizarCheckboxesDisponiveis() {
    const checkboxesPorGrupo = {};

    document.querySelectorAll('.aula-checkbox').forEach(cb => {
        const grupo = cb.dataset.grupo;
        if (!checkboxesPorGrupo[grupo]) {
            checkboxesPorGrupo[grupo] = [];
        }
        checkboxesPorGrupo[grupo].push(cb);
    });

    Object.entries(checkboxesPorGrupo).forEach(([grupoId, checkboxes]) => {
        const aulasSelecionadas = new Set();

        // Recolhe os aulaIds selecionados
        checkboxes.forEach(cb => {
            if (cb.checked) {
                aulasSelecionadas.add(cb.dataset.aula);
            }
        });

        // Atualiza o estado de todas as checkboxes
        checkboxes.forEach(cb => {
            const aulaId = cb.dataset.aula;
            const deveDesativar = aulasSelecionadas.has(aulaId) && !cb.checked;

            cb.disabled = deveDesativar;
            cb.parentElement.style.color = deveDesativar ? 'gray' : '';
        });
    });

    // atualiza o estado da checkbox Select All (fica desativada tb se todas estiverem desativadas)
    document.querySelectorAll('.aulas-simultaneas-box').forEach(box => {
        const checkboxes = box.querySelectorAll('.aula-checkbox');
        const selectAll = box.querySelector('.select-all-checkbox');

        const checkboxesAtivos = Array.from(checkboxes).filter(cb => !cb.disabled);
        const todosDesativados = Array.from(checkboxes).every(cb => cb.disabled);
        selectAll.disabled = todosDesativados;
        selectAll.parentElement.style.color = todosDesativados ? 'gray' : '';

        if (!todosDesativados) {
            const todosSelecionados = checkboxesAtivos.every(cb => cb.checked);
            const algumSelecionado = checkboxesAtivos.some(cb => cb.checked);

            selectAll.checked = todosSelecionados;
        } else {
            selectAll.checked = false;
        }
    });
}


function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        if (cookie.trim().startsWith(name + '=')) {
            return decodeURIComponent(cookie.trim().substring(name.length + 1));
        }
    }
    return '';
}

let popupGrupoId = null;
let popupBoxIndex = null;

function guardarTodasSelecoes() {
    console.log("Payload:", getAllSelectedAulas());

    // collect data, then call save
    fetch(`/parser/guardar_aulas_em_paralelo/?id=${PROJECT_ID}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        pares: getAllSelectedAulas(),
      }),
    })
      .then(async (res) => {
        const text = await res.text();
        try {
          const data = JSON.parse(text);
          if (data.status === "ok") {
            if (data.inconsistentes && data.inconsistentes.length > 0) {
              mostrarPopupInconsistentes(data.inconsistentes);
            } else {
              window.location.href = `/editturnos/${PROJECT_ID}`;
            }
            if (data.inconsistentes && data.inconsistentes.length > 0) {
              mostrarPopupInconsistentes(data.inconsistentes);
            } else {
              window.location.href = `/editturnos/${PROJECT_ID}`;
            }
          } else {
            alert("Erro ao guardar.");
          }
        } catch (e) {
          console.error("Not JSON!", text);
          alert("Erro do servidor: resposta inesperada.");
        }
      })
      .catch((err) => {
        console.error("Fetch failed:", err);
        alert("Erro na comunicação com o servidor.");
      });
}

function getAllSelectedAulas() {
    const pares = [];

    // Para cada caixa .aulas-simultaneas-box
    document.querySelectorAll('.aulas-simultaneas-box').forEach(box => {
        const aulasSelecionadas = [];

        // Recolhe checkboxes marcadas dentro da caixa
        box.querySelectorAll('.aula-checkbox:checked').forEach(cb => {
            const aulaId = cb.dataset.aula;
            const turmas = cb.dataset.turmas.split(',');
            const primeiraTurma = turmas[0].trim();
            aulasSelecionadas.push({ aulaId, turma: primeiraTurma });
        });

        // Formar a "cadeia" de aulas correspondente à caixa      exemplo do que estou a referir com "cadeia" -> (Aula1, Aula2), (Aula2, Aula3),...
        for (let i = 0; i < aulasSelecionadas.length - 1; i++) {
            const a1 = aulasSelecionadas[i];
            const a2 = aulasSelecionadas[i + 1];
            pares.push([a1.aulaId, a2.aulaId, a1.turma, a2.turma]);
        }
    });

    return pares;
}




// verificar se há grupos com apenas uma turma selecionada
// se sim desativar o botão de 'Guardar Seleção' e pôr aviso
function validarGrupos() {
    let algumInvalido = false;

    document.querySelectorAll('.aulas-simultaneas-box').forEach(box => {
        const checkboxes = box.querySelectorAll('.aula-checkbox');
        const selecionadas = Array.from(checkboxes).filter(cb => cb.checked);

        if (selecionadas.length === 1) {
            algumInvalido = true;
        }
    });

    const btn = document.getElementById("btn-guardar");
    btn.disabled = algumInvalido;
    btn.classList.toggle('disabled', algumInvalido);

    const avisoFinal = document.getElementById("aviso-uma-aula-so-selecionada");
    if (algumInvalido) {
        avisoFinal.style.display = "block";
        avisoFinal.innerHTML = "Um grupo de aulas em paralelo não de ser formado por apenas uma aula.";
    } else {
        avisoFinal.style.display = "none";
        avisoFinal.innerHTML = "";
    }
}

function aplicarSelectAllListeners() {
    document.querySelectorAll('.select-all-checkbox').forEach(selectAll => {
        const turmasList = selectAll.closest('.aulas-simultaneas-box');
        const checkboxes = turmasList.querySelectorAll('.aula-checkbox');

        // Evento: clicar em "Selecionar todas"
        selectAll.addEventListener('change', function () {
            checkboxes.forEach(cb => {
                if (!cb.disabled) {
                    cb.checked = this.checked;
                }
            });
            atualizarCheckboxesDisponiveis();
            validarGrupos();
        });

        // Evento: clicar em qualquer aula individual
        checkboxes.forEach(cb => {
            cb.addEventListener('change', function () {
                const allEnabled = Array.from(checkboxes).filter(cb => !cb.disabled);
                const allChecked = allEnabled.every(cb => cb.checked);
                const someChecked = allEnabled.some(cb => cb.checked);

                if (allChecked) {
                    selectAll.checked = true;
                } else {
                    selectAll.checked = false;
                }
                atualizarCheckboxesDisponiveis();
                validarGrupos();
            });
        });
    });
}

function cancelarMudancas() {
    window.location.href = `/editturnos/${PROJECT_ID}`;
}


function preencherCheckboxesComAulasEmParalelo(aulasEmParalelo) {
    const boxes = document.querySelectorAll('.aulas-simultaneas-box');

    let usadas = new Set();

    aulasEmParalelo.forEach((cadeia) => {
      for (let box of boxes) {
        const boxId = box.dataset.grupo + "__" + box.dataset.boxIndex;
        if (usadas.has(boxId)) continue;

        const checkboxes = Array.from(box.querySelectorAll(".aula-checkbox"));
        const aulaIdsNaBox = new Set(checkboxes.map((cb) => cb.dataset.aula));

        if (cadeia.every((aulaId) => aulaIdsNaBox.has(String(aulaId)))) {
          console.log("Preenchida cadeia:", cadeia, "na box:", boxId);
          checkboxes.forEach((cb) => {
            if (cadeia.map(String).includes(cb.dataset.aula)) {
              cb.checked = true;
            }
          });

          usadas.add(boxId);
          break;
        }
      }
    });

    atualizarCheckboxesDisponiveis();
    validarGrupos();
}

function mostrarPopupInconsistentes(cadeias) {
    const div = document.getElementById("lista-inconsistentes");
    div.innerHTML = "";

    cadeias.forEach((grupo, i) => {
        div.innerHTML += `<div><strong>Grupo ${i + 1}: ${grupo.nome_uc}</strong><br>`;
        grupo.aulas.forEach(aula => {
            div.innerHTML += `<div style="margin-left: 10px;">- ${aula}</div>`;
        });
        div.innerHTML += `</div><br>`;
    });

    document.getElementById("popup-inconsistentes").style.display = "block";
}


function fecharPopupInconsistentes() {
    document.getElementById("popup-inconsistentes").style.display = "none";
    window.location.href = `/editturnos/${PROJECT_ID}`;
}

function mostrarPopupInconsistentes(cadeias) {
    const div = document.getElementById("lista-inconsistentes");
    div.innerHTML = "";

    cadeias.forEach((grupo, i) => {
        div.innerHTML += `<div><strong>Grupo ${i + 1}: ${grupo.nome_uc}</strong><br>`;
        grupo.aulas.forEach(aula => {
            div.innerHTML += `<div style="margin-left: 10px;">- ${aula}</div>`;
        });
        div.innerHTML += `</div><br>`;
    });

    document.getElementById("popup-inconsistentes").style.display = "block";
}


function fecharPopupInconsistentes() {
    document.getElementById("popup-inconsistentes").style.display = "none";
    window.location.href = `/editturnos/${PROJECT_ID}`;
}