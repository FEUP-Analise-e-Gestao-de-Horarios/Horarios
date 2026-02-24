// static/js/uc_view.js
$(document).ready(function() {
    // Initialize popovers
    $('[data-toggle="popover"]').popover({
        trigger: 'hover',
        html: true
    });

    // Set proper heights for aula boxes
    function setAulaHeights() {
        var baseHeight = $('#table_vistas tbody tr:first td').outerHeight();
        $('.aula-box').each(function() {
            var rowspan = parseInt($(this).attr('data-rowspan')) || 1;
            $(this).css('height', (baseHeight * rowspan) + 'px');
        });
    }
    setAulaHeights();

    // Track selected element for both teachers and classes
    let selectedElement = null;

    // Handle clicks for both teachers and class boxes
    $(document).on('click', '.teacher-acronym, .aula-box, .schedule-cell', function(e) {
        e.stopPropagation();
        const $element = $(this);
        
        // Determine what was clicked
        let elementType;
        if ($element.hasClass('teacher-acronym')) {
            elementType = 'teacher';
        } else if ($element.hasClass('aula-box')) {
            elementType = 'class';
        } else if ($element.hasClass('schedule-cell')) {
            elementType = 'cell';
        }

        if (!selectedElement) {
            // First selection
            if (elementType === 'cell') {
                // Can't select empty cell first
                return;
            }
            
            selectedElement = {
                element: $element,
                type: elementType,
                id: elementType === 'teacher' ? $element.data('teacher-id') : $element.data('aula-id'),
                text: elementType === 'teacher' ? $element.text() : $element.find('.teacher-acronym').first().text(),
                aulaElement: elementType === 'teacher' ? $element.closest('.aula-box') : $element
            };
            $element.addClass('selected');
        } else {
            // Second selection - handle different combinations
            if (selectedElement.type === 'teacher' && elementType === 'teacher') {
                // Teacher swap - removed confirm dialog
                swapTeachers(
                    selectedElement.aulaElement.data('aula-id'),
                    selectedElement.id,
                    $element.closest('.aula-box').data('aula-id'),
                    $element.data('teacher-id'),
                    selectedElement.element,
                    $element
                );
            } else if (selectedElement.type === 'class' && elementType === 'cell') {
                // Move class to empty cell
                const $targetCell = $element;
                const newDia = $targetCell.data('dia');
                const newHora = $targetCell.data('hora');
                
                moveClassToCell(
                    selectedElement.id,
                    newDia,
                    newHora,
                    selectedElement.element,
                    $targetCell
                );
            } else if (selectedElement.type === 'class' && elementType === 'class') {
                // Class swap
                swapClasses(
                    selectedElement.id,
                    $element.data('aula-id'),
                    selectedElement.element,
                    $element
                );
            } else {
                alert("Invalid selection combination");
            }
            
            // Reset selection
            $('.selected').removeClass('selected');
            selectedElement = null;
        }
    });

    // New function to move class to empty cell
    function moveClassToCell(aulaId, newDia, newHora, $aulaElement, $targetCell) {
        // Show loading state
        $aulaElement.css('opacity', '0.5');

        $.ajax({
            url: `/editturnos/${projId}/uc_changes/`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                type: 'move',
                aulaId: aulaId,
                newDia: newDia,
                newHora: newHora,
                csrfmiddlewaretoken: csrfToken
            }),
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                if (response.success) {
                    // Update UI
                    $aulaElement.attr({
                        'data-dia': newDia,
                        'data-hora-inicial': newHora
                    });
                    
                    // Move the aula to the new cell
                    const $aulaContainer = $aulaElement.closest('.aula-container').detach();
                    $targetCell.empty().append($aulaContainer);
                    
                    if (response.conflicts && response.conflicts.length > 0) {
                        alert('Move completed with conflicts:\n' + response.conflicts.join('\n'));
                    }
                } else {
                    alert('Error: ' + (response.error || 'Failed to move class'));
                }
            },
            error: function(xhr, status, error) {
                alert('Error connecting to server');
            },
            complete: function() {
                $aulaElement.css('opacity', '1');
            }
        });
    }

    // Function to swap classes
    function swapClasses(aula1Id, aula2Id, $element1, $element2) {
        // Get current positions
        const dia1 = $element1.data('dia');
        const hora1 = $element1.data('hora-inicial');
        const dia2 = $element2.data('dia');
        const hora2 = $element2.data('hora-inicial');
        
        // Show loading state
        $element1.css('opacity', '0.5');
        $element2.css('opacity', '0.5');

        $.ajax({
            url: `/editturnos/${projId}/swap_aulas/`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                aula1: {
                    id: aula1Id,
                    newDia: dia2,
                    newHora: hora2
                },
                aula2: {
                    id: aula2Id,
                    newDia: dia1,
                    newHora: hora1
                },
                csrfmiddlewaretoken: csrfToken
            }),
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                if (response.success) {
                    // Update UI positions
                    $element1.attr({
                        'data-dia': dia2,
                        'data-hora-inicial': hora2
                    });
                    $element2.attr({
                        'data-dia': dia1,
                        'data-hora-inicial': hora1
                    });
                    
                    // Move elements to new positions in the table
                    const $cell1 = $element1.closest('td');
                    const $cell2 = $element2.closest('td');
                    
                    // Swap the aula-container contents
                    const $container1 = $cell1.find('.aula-container').detach();
                    const $container2 = $cell2.find('.aula-container').detach();
                    
                    $cell1.append($container2);
                    $cell2.append($container1);
                    
                    if (response.conflicts && response.conflicts.length > 0) {
                        alert('Swap completed with conflicts:\n' + response.conflicts.join('\n'));
                    }
                } else {
                    alert('Error: ' + (response.error || 'Failed to swap classes'));
                }
            },
            error: function(xhr, status, error) {
                alert('Error connecting to server');
            },
            complete: function() {
                $element1.css('opacity', '1');
                $element2.css('opacity', '1');
            }
        });
    }

    // Function to swap teachers
    function swapTeachers(aula1Id, teacher1Id, aula2Id, teacher2Id, $teacher1Element, $teacher2Element) {
        // Show loading state
        const originalTeacher1 = $teacher1Element.text();
        const originalTeacher2 = $teacher2Element.text();
        $teacher1Element.text('Swapping...');
        $teacher2Element.text('Swapping...');

        $.ajax({
            url: `/editturnos/${projId}/swap_teachers/`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                aula1: { id: aula1Id },
                aula2: { id: aula2Id },
                teacher1: teacher1Id.toString(),
                teacher2: teacher2Id.toString(),
                csrfmiddlewaretoken: csrfToken
            }),
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                if (response.success) {
                    // Update UI with the returned teacher abbreviations
                    $teacher1Element.text(response.new_teacher1_abbreviation);
                    $teacher2Element.text(response.new_teacher2_abbreviation);
                    
                    // Update data attributes
                    $teacher1Element.data('teacher-id', teacher2Id);
                    $teacher2Element.data('teacher-id', teacher1Id);
                } else {
                    // Revert on error
                    $teacher1Element.text(originalTeacher1);
                    $teacher2Element.text(originalTeacher2);
                    alert('Error: ' + (response.error || 'Failed to swap teachers'));
                }
            },
            error: function(xhr, status, error) {
                // Revert on error
                $teacher1Element.text(originalTeacher1);
                $teacher2Element.text(originalTeacher2);
                alert('Error connecting to server');
            }
        });
    }

    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});