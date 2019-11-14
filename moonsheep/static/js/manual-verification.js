function support_manual_verification(data) {
    for (let [fld, values] of Object.entries(data)) {
        let input = jQuery(`input[name="${fld}"]`)
        if (values.length == 1) {
            // set chosen value
            input.val(values[0])
            // color it
            input.css('outline', 'lime solid 3px') // TODO set class

        } else if (values.length > 0) {
            // color it
            input.css('outline', 'orangered solid 3px') // TODO set class
            // set hover / popup
            // TODO https://www.w3schools.com/css/css_tooltip.asp
        }
    }
}

