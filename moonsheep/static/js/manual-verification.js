function support_manual_verification(data) {
    for (let [fld, values] of Object.entries(data)) {
        let input = jQuery(`input[name="${fld}"]`)
        if (values.length == 1) {
            // set chosen value
            msSetValue(input, values[0]);

            // color it
            input.addClass('ms-field-verified');

        } else if (values.length > 0) {
            // color it
            input.addClass('ms-field-fuzzy');

            // set hover with options
            let options = ``;
            // TODO test escaping of $val
            values.forEach(val => options += `<div class="ms-option" data-value="${val}">${val}</div>`);

            // tooltip is placed as sibling to input
            const tooltip = new Tooltip(input[0], {
                placement: 'bottom',
                template: `<div class="ms-values-tooltip"></div>`,
                innerSelector: '.ms-values-tooltip',
                html: true,
                title: options,
                trigger: "hover",
            });
            tooltip.show();
            jQuery(input).data('tooltip', tooltip);
        }
    }

    // setting values on click
    jQuery( '.ms-option' ).click(function(ev) {
        let option = jQuery(this);
        let value = option.data('value');
        let input = option.parents('.ms-values-tooltip').siblings('input');
        let tooltip = input.data('tooltip');

        msSetValue(input, value);

        ev.stopPropagation();
        ev.preventDefault();
        tooltip.hide();
    });
}

function msSetValue(input, value) {
    if (input.attr('type') == 'checkbox') {
        input.prop('checked', value);

    } else {
        input.val(value);
    }
}