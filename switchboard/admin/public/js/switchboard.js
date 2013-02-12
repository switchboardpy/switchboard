/*global alert, confirm, jQuery, Handlebars, SWITCHBOARD */
jQuery(function($) {
    var $sb = $('.switchboard'),
        $drawer = $('.drawer', $sb);
    $(document).ajaxStart(function() {
        $('.spinner', $sb).show();
    });
    $(document).ajaxStop(function() {
        $('.spinner', $sb).hide();
    });
    var api = function (url, params, succ) {
        $.ajax({
            url: url,
            type: 'POST',
            data: params,
            dataType: 'json',
            success: function (resp) {
                if (resp.success) {
                    succ(resp.data);
                } else {
                    alert(resp.data);
                }
            },
            failure: function () {
                alert('There was an internal error. Data probably wasn\'t saved');
            }
        });
    };

    // Compile templates
    Handlebars.registerHelper('ifToggled', function(status, options) {
        if (this.status === status) {
            return options.fn(this);
        }
    });
    var templates = {};
    $('script[type*="template"]').each(function() {
        templates[this.id] = Handlebars.compile($(this).html());
    });

    // Events

    $('.add-switch', $sb).on('click', function(e) {
        e.preventDefault();
        var html = templates.switchForm({add: true});
        $drawer.html(html).show();
        $drawer.children('input:first').focus();
    });

    $('.switches', $sb).on('click', '.edit', function(e) {
        e.preventDefault();
        var $row = $(this).parents('tr:first');
        var html = templates.switchForm({
            add:           false,
            curkey:        $row.attr('data-switch-key'),
            key:           $row.attr('data-switch-key'),
            label:         $row.attr('data-switch-label'),
            description:   $row.attr('data-switch-description')
        });
        $drawer.html(html).show();
        $drawer.children('input:first').focus();
    });

    $('.switches', $sb).on('click', '.delete', function(e) {
        e.preventDefault();
        var $row = $(this).parents('tr:first');
        var $table = $row.parents('table:first');

        if (!confirm('Are you SURE you want to remove this switch?')) {
            return;
        }

        api(SWITCHBOARD.deleteSwitch, { key: $row.attr('data-switch-key') },
            function () {
                $row.remove();
                if (!$table.find('tr').length) {
                    $('.no-switches', $sb).show();
                }
            });
    });

    $('.switches', $sb).on('click', '.status .btn', function(e) {
        e.preventDefault();
        var $row = $(this).parents('tr:first');
        var $el = $(this);
        var status = parseInt($el.attr('data-status'), 10);
        var labels = {
            4: "(Inherit from parent)",
            3: "(Active for everyone)",
            2: "(Active for conditions)",
            1: "(Disabled for everyone)"
        };

        if (status === 3) {
            if (!confirm('Are you SURE you want to enable this switch globally?')) {
                return;
            }
        }

        api(SWITCHBOARD.updateStatus,
            {
                key:    $row.attr('data-switch-key'),
                status: status
            },

            function (swtch) {
                if (swtch.status === status) {
                    $row.find('.toggled').removeClass('toggled');
                    $el.addClass('toggled');
                    $row.attr('data-switch-status', swtch.status);
                    if ($.isArray(swtch.conditions) && swtch.conditions.length < 1 && swtch.status === 2) {
                        swtch.status = 3;
                    }
                    $row.find('.status .inner').text(labels[swtch.status]);
                }
            });
    });

    $('.switches', $sb).on('click', '.add-condition a', function(e) {
        e.preventDefault();
        var $form = $(this).parents('td:first').find('.conditions-form:first');

        if ($form.is(':hidden')) {
            $form.html(templates.switchConditions({}));
            $form.show();
        } else {
            $form.hide();
        }
    });

    $('.switches', $sb).on('change', '.conditions-form select', function() {
        var field = $(this).val().split(',');
        $(this).
            parents('tr:first').
            find('div.fields').hide();

        $(this).
            parents('tr:first').
            find('div[data-path="' + field[0] + '.' + field[1] + '"]').show();
    });

    $('.switches', $sb).on('submit', '.conditions-form form', function(e) {
        e.preventDefault();
        var $form = $(this);

        var data = {
            key: $form.parents('tr:first').attr('data-switch-key'),
            id: $form.attr('data-switch'),
            field: $form.attr('data-field')
        };

        $.each($form.find('input'), function () {
            var val,
                $input = $(this);

            if ($input.attr('type') === 'checkbox') {
                val = $input.is(':checked') ? '1' : '0';
            } else {
                val = $input.val();
            }
            data[$input.attr('name')] = val;
        });

        api(SWITCHBOARD.addCondition, data, function (swtch) {
            var result = templates.switchData(swtch);
            $('.switches tr[data-switch-key=' + data.key + ']', $sb).replaceWith(result);
        });
    });

    $('.switches', $sb).on('click', '.conditions .delete-condition', function(e) {
        e.preventDefault();

        var $el = $(this).parents('span:first');

        var data = {
            key:   $el.parents('tr:first').attr('data-switch-key'),
            id:    $el.attr('data-switch'),
            field: $el.attr('data-field'),
            value: $el.attr('data-value')
        };

        api(SWITCHBOARD.delCondition, data, function (swtch) {
            var result = templates.switchData(swtch);
            $('.switches tr[data-switch-key=' + data.key + ']').replaceWith(result);
        });

    });

    $drawer.on('click', '.cancel', function(e) {
        e.preventDefault();
        $drawer.hide();
    });

    $drawer.on('click', '.submit-switch', function(e) {
        e.preventDefault();
        var action = $(this).attr('data-action');
        var curkey = $(this).attr('data-curkey');

        api(action === 'add' ? SWITCHBOARD.addSwitch : SWITCHBOARD.updateSwitch,
            {
                curkey: curkey,
                label: $('input[name=label]', $drawer).val(),
                key: $('input[name=key]', $drawer).val(),
                description: $('textarea', $drawer).val()
            },

            function (swtch) {
                var result = templates.switchData(swtch);

                if (action === 'add') {
                    if ($('.switches tr', $sb).length === 0) {
                        $('.switches', $sb).html(result);
                        $('.switches', $sb).removeClass('empty');
                        $('.no-switches', $sb).hide();
                    } else {
                        $('.switches tr:last', $sb).after(result);
                    }

                    $drawer.hide();
                } else {
                    $('.switches tr[data-switch-key=' + curkey + ']', $sb).replaceWith(result);
                    $drawer.hide();
                }
                //$(result).click();
            }
        );
    });

    $('input[type=search]').keyup(function () {
        var query = $(this).val();
        $('.switches tr', $sb).removeClass('hidden');
        if (!query) {
            return;
        }
        $('.switches tr', $sb).each(function (_, el) {
            var $el = $(el);
            var score = 0;
            score += $el.attr('data-switch-key').score(query);
            score += $el.attr('data-switch-label').score(query);
            if ($el.attr('data-switch-description')) {
                score += $el.attr('data-switch-description').score(query);
            }
            if (score === 0) {
                $el.addClass('hidden');
            }
        });
    });
});
