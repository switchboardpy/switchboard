<%!
  '''
  Template helper functions, stored here so they can be used no matter what
  web framework is being used.
  '''
  def sort_by_key(field, currently):
    is_negative = currently.find('-') == 0
    current_field = currently.lstrip('-')

    if current_field == field and is_negative:
      return field
    elif current_field == field:
      return '-' + field
    else:
      return field

  from datetime import datetime
  def timesince(dt):
    if isinstance(dt, str):
      dt = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f')
    delta = datetime.utcnow() - dt
    days = delta.days + float(delta.seconds) / 86400
    if days > 1:
      return '%d days' % round(days)
    # since days is < 1, a fraction, we multiply to get hours
    hours = days * 24
    if hours > 1:
      return '%d hours' % round(hours)
    minutes = hours * 60
    if minutes > 1:
      return '%d minutes' % round(minutes)
    seconds = minutes * 60
    return '%d seconds' % round(seconds)
%>
<!DOCTYPE html>
<html>
  <head>
    <title>Switchboard</title>
    <link rel="stylesheet" href="//cdnjs.cloudflare.com/ajax/libs/normalize/3.0.0/normalize.min.css">
    <link rel="stylesheet" href="//cdnjs.cloudflare.com/ajax/libs/font-awesome/4.0.3/css/font-awesome.min.css">
    % if  hasattr(settings, 'SWITCHBOARD_ADMIN_BASE_URL'):
    <base href="${settings.SWITCHBOARD_ADMIN_BASE_URL}">
    % endif
    <style type="text/css">
      * { -moz-box-sizing: border-box; -webkit-box-sizing: border-box; box-sizing: border-box; }
      /* typography - lifted from Typeplate, http://typeplate.com/ */
      html { font: 112.5%/1.65 "HelveticaNeue-Light", "Helvetica Neue Light", "Helvetica Neue", Helvetica, Arial, "Lucida Grande", sans-serif; font-weight: 300; }
      body { -webkit-hyphens: auto; -moz-hyphens: auto; -ms-hyphens: auto; hyphens: auto; word-wrap: break-word; color: #444; }
      h1, h2, h3, h4, h5, h6 { text-rendering: optimizeLegibility; line-height: 1; margin-top: 0; color: #222; }
      .tera { font-size: 117px; font-size: 6.5rem; margin-bottom: 0.25385rem; }
      .giga { font-size: 90px; font-size: 5rem; margin-bottom: 0.33rem; }
      .mega { font-size: 72px; font-size: 4rem; margin-bottom: 0.4125rem; }
      h1, .alpha { font-size: 60px; font-size: 3.33333rem; margin-bottom: 0.495rem; }
      h2, .beta { font-size: 48px; font-size: 2.66667rem; margin-bottom: 0.61875rem; }
      h3, .gamma { font-size: 36px; font-size: 2rem; margin-bottom: 0.825rem; }
      h4, .delta { font-size: 24px; font-size: 1.33333rem; margin-bottom: 1.2375rem; }
      h5, .epsilon { font-size: 21px; font-size: 1.16667rem; margin-bottom: 1.41429rem; }
      h6, .zeta { font-size: 18px; font-size: 1rem; margin-bottom: 1.65rem; }
      .micro { font-size: 12px; font-size: 0.67777rem; margin-bottom: 0.94444rem; }
      p { margin: 0 0 1.5em; }
      p + p { text-indent: 1.5em; margin-top: -1.5em; }
      /* more typography, Switchboard-specific (i.e., not from Typelate) */
      .switchboard .sort { line-height: 2.16667rem; }
      .switchboard input[type="search"] { margin-left: 1rem; }
      /* general */
      #content { width: 80%; margin: 0 auto; }
      .switchboard { margin-bottom: 2rem; margin-top: 132px; }
      .switchboard a { display: inline-block; padding: 0 0.25em; border-radius: 4px; color: #666; text-decoration: underline; -webkit-transition: background-color .1s linear; transition: background-color .1s linear; }
      .switchboard a:link { color: #666; text-decoration: underline; }
      .switchboard a:visited { color: #555; }
      .switchboard a:hover { color: #fff; background-color: #666; text-decoration: none; }
      .switchboard a:active { color: #fff; background-color: #555; text-decoration: none; }
      .switchboard .hidden { display: none; }
      .switchboard .btn,
      .switchboard .btn:link,
      .switchboard .btn:visited {
        background-color: #f5f5f5;
        border: 1px solid #bbb;
        border-bottom-color: #a2a2a2;
        color: inherit;
        text-decoration: none;
        display: inline-block;
        padding: 4px 12px;
        font-size: 14px;
        margin-bottom: 0;
        text-align: center;
        vertical-align: middle;
        cursor: pointer;
        text-shadow: 0 1px 1px rgba(255,255,255,0.75);
        border-radius: 4px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.2),0 1px 2px rgba(0,0,0,.05);
        background-image: -webkit-linear-gradient(top,#fff,#e6e6e6);
        background-image: linear-gradient(to bottom,#fff,#e6e6e6);
        background-repeat: repeat-x;
      }
      .switchboard .btn:hover { background-color: #e6e6e6; background-position: 0 -15px; -webkit-transition: background-position .1s linear; transition: background-position .1s linear; }
      .switchboard .btn:active { background-color: #f5f5f5; border: 1px solid #bbb; border-bottom-color: #a2a2a2; color: inherit; text-decoration: none; display: inline-block; padding: 4px 12px; margin-bottom: 0; text-align: center; vertical-align: middle; cursor: pointer; text-shadow: 0 1px 1px rgba(255,255,255,0.75); border-radius: 4px; box-shadow: inset 0 1px 0 rgba(255,255,255,.2),0 1px 2px rgba(0,0,0,.05); background-image: -webkit-linear-gradient(top,#fff,#e6e6e6); background-image: linear-gradient(to bottom,#fff,#e6e6e6); background-repeat: repeat-x; }
      .switchboard .btn-group { position: relative; display: inline-block; font-size: 0; vertical-align: middle; white-space: nowrap; }
      .switchboard .btn-group > .btn:first-child { margin-left: 0; border-top-left-radius: 4px; border-bottom-left-radius: 4px; }
      .switchboard .btn-group > .btn { position: relative; border-radius: 0; }
      .switchboard .btn-group > .btn + .btn { margin-left: -1px; }
      .switchboard .btn-group > .btn:last-child { border-top-right-radius: 4px; border-bottom-right-radius: 4px; }
      .switchboard .btn-link, .switchboard .btn-link:link { background-color: transparent; background-image: none; box-shadow: none; border-radius: 0; border-color: transparent; }
      .switchboard .btn-link:hover { background-color: transparent; }
      .switchboard select, .switchboard input, .switchboard textarea { font-size: 0.7778rem; margin: 0; display: inline-block; vertical-align: middle; border-radius: 4px; line-height: 1.8333rem; background-color: #fff; border: 1px solid #ccc; }
      .switchboard textarea { line-height: 1.5em; }
      .switchboard select, .switchboard input { height: 1.8333rem; }
      .switchboard select { cursor: pointer; }
      .switchboard input { box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.075); -webkit-transition: border linear 0.2s, box-shadow linear 0.2s; transition: border linear 0.2s, box-shadow linear 0.2s; }
      /* header */
      .switchboard .icon { float: left; margin: 6px 0.25em 6px 0; }
      .switchboard > header { position: fixed; top: 0; width: 80%; background-color: rgba(255, 255, 255, 0.9); border-bottom: 1px solid #ccc; padding-top: 0.825rem; z-index: 2; }
      .switchboard .spinner { font-size: 2.5rem; }
      /* messages */
      .switchboard .messages { position: absolute; top: 0; right: 0; width: 33%; }
      .switchboard .message { text-shadow: 0 1px 0 rgba(255, 255, 255, 0.5); border-radius: 4px; }
      /* default hidden state */
      .switchboard .message { display: none; border: 1px solid; padding: 1rem; margin-bottom: 0.4rem; }
      /* active visible state */
      .switchboard .message.active { display: block; }
      .switchboard .message p { margin: 0; }
      .switchboard .message.error { border-color: #eed3d7; background-color: rgba(242, 222, 222, 0.9); color: #b94a48; }
      .switchboard .message.warning { border-color: #fbeed5; background-color: rgba(252, 248, 227, 0.9); color: #c09853; }
      .switchboard .message.info { border-color: #bce8f1; background-color: rgba(217, 237, 247, 0.9); color: #3a87ad; }
      .switchboard .message.success { border-color: #d6e9c6; background-color: rgba(223, 240, 216, 0.9); color: #468847; }
      .switchboard .message .close { display: none; position: relative; top: -0.5em; right: -0.25em; line-height: 20px; padding: 0; cursor: pointer; background: transparent; border: 0; -webkit-appearance: none; font-size: 20px; float: right; font-weight: bold; text-shadow: 0 1px 0 #fff; color: #000; opacity: 0.2; }
      .switchboard .message.active .close { display: block; }
      /* toolbar */
      .switchboard .toolbar { margin-bottom: 0.825rem; }
      .switchboard .sort, .switchboard .sort li { margin: 0; padding: 0; list-style: none; }
      .switchboard .sort { padding-right: 0.5rem; }
      .switchboard .sort li { display: inline-block; margin-right: 0.25em; }
      .switchboard .sort { border-right: 1px solid #bbb; }
      .switchboard .sort, input[type="search"] { float: right; }
      .switchboard .toolbar[data-sort="-label"] .sort .label a,
      .switchboard .toolbar[data-sort="-date_created"] .sort .date_created a,
      .switchboard .toolbar[data-sort="-date_modified"] .sort .date_modified a,
      .switchboard .toolbar[data-sort="label"] .sort .label a,
      .switchboard .toolbar[data-sort="date_created"] .sort .date_created a,
      .switchboard .toolbar[data-sort="date_modified"] .sort .date_modified a,
      .switchboard .toolbar[data-sort=""] .sort .date_modified a {
        font-weight: bold;
        color: #333;
      }
      .switchboard .toolbar[data-sort="-label"] .sort .label a:hover,
      .switchboard .toolbar[data-sort="-date_created"] .sort .date_created a:hover,
      .switchboard .toolbar[data-sort="-date_modified"] .sort .date_modified a:hover,
      .switchboard .toolbar[data-sort="label"] .sort .label a:hover,
      .switchboard .toolbar[data-sort="date_created"] .sort .date_created a:hover,
      .switchboard .toolbar[data-sort="date_modified"] .sort .date_modified a:hover,
      .switchboard .toolbar[data-sort=""] .sort .date_modified a:hover {
        color: #fff;
      }
      .switchboard .toolbar[data-sort="-label"] .sort .label a:after,
      .switchboard .toolbar[data-sort="-date_created"] .sort .date_created a:after,
      .switchboard .toolbar[data-sort="-date_modified"] .sort .date_modified a:after {
        content: " ▴";
      }
      .switchboard .toolbar[data-sort="label"] .sort .label a:after,
      .switchboard .toolbar[data-sort="date_created"] .sort .date_created a:after,
      .switchboard .toolbar[data-sort="date_modified"] .sort .date_modified a:after,
      .switchboard .toolbar[data-sort=""] .sort .date_modified a:after {
        content: " ▾";
      }
      /* table */
      .switchboard .switches { width: 100%; collapse; margin-bottom: 1.65rem; }
      .switchboard .switches .switch { border-top: 1px solid #bbb; padding: 1.65rem 0; position: relative; }
      .switchboard .switches .switch.overlayed { opacity: 0.6; }
      .switchboard .switches .switch > div { vertical-align: top; overflow:hidden; }
      /* names */
      .switchboard .switches .name { margin-bottom: 0.825rem; }
      .switchboard .switches .title { margin-bottom: 0.41429rem; }
      .switchboard .switches .timestamp { color: #999; font-weight: normal; margin-bottom: 0; }
      .switchboard .switches .name small { color: #666; }
      .switchboard .switches .description, .switchboard .switches .description p { margin-bottom: 0; }
      /* statuses */
      .switchboard .switches .status { text-align: right; width: 100%; position: absolute; right: 0; top: 1.65rem; }
      .switchboard .switches .status label { display: inline-block; font-weight: bold; color: #222; }
      .switchboard .switches .status label:after { content: ':'; }
      .switchboard .switches .status select, .switchboard input[type="search"] { width: 25%; }
      .switchboard .switch[data-switch-status="1"] .status select { border-left: 10px solid #cc4036; }
      .switchboard .switch[data-switch-status="2"] .status select { border-left: 10px solid #faa732; }
      .switchboard .switch[data-switch-status="3"] .status select { border-left: 10px solid #5bb75b; }
      .switchboard .switch[data-switch-status="4"] .status select { border-left: 10px solid #006dcc; }
      /* metadata */
      .switchboard .switches .metadata { clear: both; }
      /* actions */
      .switchboard .switches .actions { visibility: hidden; }
      .switchboard .switches .switch:hover .actions { visibility: visible; margin: 0 0 0 1em; }
      .switchboard .switches .actions .btn-link { padding: 0; border: 0; margin-left: 0.5em; }
      /* drawer */
      .switchboard .drawer { display: none; margin-bottom: 1em; position: absolute; background-color: #efefef; z-index: 1; opacity: 0.9; padding: 1rem; left: 20%; width: 60%; border: 1px solid #ccc; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px; }
      .switchboard .drawer.header { position: fixed; z-index: 2; }
      .switchboard .drawer .field { margin-bottom: 1em; }
      .switchboard .drawer label { display: block; font-weight: bold; }
      .switchboard .drawer input, .switchboard .drawer textarea { width: 50%; }
      .switchboard .drawer .close-action { float: right; cursor: pointer; }
      /* conditions */
      .switchboard .conditions-form { overflow: hidden; margin-top: 0.825rem; }
      .switchboard .conditions-form select, .switchboard .conditionsForm .fields { float: left; margin-right: 0.5em; }
      .switchboard .conditions label { font-weight: bold; margin-right: 0.25em; width: 8em; display: inline-block; }
      .switchboard .conditions label:after { content: ":"; }
      .switchboard .conditions .value { padding: 0 0.25em; margin-right: 0.25em; background-color: #e6e6e6; }
      .switchboard .conditions .delete-condition { margin-left: 0.25em; margin-top: -4px; padding: 0; border: 0; color: #666; }
      .switchboard .group { overflow-x: auto; }
      /* versions */
      .switchboard .version-date { border-bottom: 1px solid #ccc; padding: 1rem 0; font-size: 0.8rem; }
      .switchboard .version-date:last-child { border-bottom: none; }
      .switchboard .version-date h6 { margin-bottom: 1rem; }
      .switchboard .version { margin-bottom: 0.5rem; clear: both; overflow: auto; }
      .switchboard .version-summary { float: left; }
      .switchboard .version-meta { float: right; font-style: italic; color: #666; }
      .switchboard .changed { font-weight: 600; }
      .switchboard .status-label-1 .fa-circle { color: #cc4036; }
      .switchboard .status-label-2 .fa-circle { color: #faa732; }
      .switchboard .status-label-3 .fa-circle { color: #5bb75b; }
      .switchboard .status-label-4 .fa-circle { color: #006dcc; }
      .switchboard .no-history p { margin-bottom: 0; }
    </style>
    <script>
      var SWITCHBOARD = {
        addSwitch:    "add",
        updateSwitch: "update",
        deleteSwitch: "delete",
        updateStatus: "status",
        addCondition: "add_condition",
        delCondition: "remove_condition",
        history:      "history"
      };
    </script>
  </head>
  <body>
    <div id="content">
      <div class="switchboard">
        <header class="page-header">
          <h1 class="branding">
            <img class="icon" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAIAAADYYG7QAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJ bWFnZVJlYWR5ccllPAAAAp5JREFUeNrsWc1uEzEQnkkCSpRDcmmyPByob1J4kN76Htx5AuBCJaCo pVJ72xySNeOdrDPrXXvy44CROpXc7cYZf/6+mfFP8fOXr/P5DA40pJ8z2NPz82g+my0uLiAPM8aM jG1NLoCAANWIIBtEI8iPoZwAmcwkM1aynBiCbLMM/hPJEDabzcP9Q8IhF8vFcDiMShYBZIDQPD7+ nkwm5AURuR0I4z+pdWlSVRW3XSvLkvoURcGzDUhW/4qIOh6Pp9PpsDEa3nt2yBwO4pVbNvfMU98O ZwKSaXXITgQbk8+OGweLBmaSsG1bR81zZDhbh5RK3Xzk4TZtY5mcyQ7eV7Qqs19h9Mag4Wmu3PJ7 ood7MjKWqYtVegtmmbp0OARMuzdjVo1NIu4av9clUwsju5NQHBp671KMAfUmmotr1yFWGGE/hqQj xiG5kWkf56kX0G7/WUumVGo3OacRJ5QE1CUvVJBEnrSIkau9gmhXQtoyccJ7gdWbgBIZ9CJqxxBU Wgyt1+tuafaKUygfJSyaGETrMJmNoT0Z8riRdTLCUA+gKs5QrVkcEDPU5aZbC7okyWBSGdpKFs+y 64/X3gqwSw0Mpq8Xqk79q7fvo2mv7hgRbz7dJNx+XL37EF+plEptKXiVcguGB1bqPg1eQ2i3cPS2 MC6Z7NHXNwlDxo/6IyWzlCWVjByqkmnbj7SAlMVVP5dhakB4WpZhE9SnxY10qElmzi+Z2Vsyu/2A 2LkMU0tGDuOHnDqGIHguw78b1PrZfoADe4WUkCE6HZjq+LN98Wb57fI2IaBiufxx9+v4U8f3n3dp 9Yo7rA+KWd0xAmR2P2Re7hiDuy55LfzPr9BM5tfC5wSEeCCgugybc0750C+MyrI8jaGU/6darVZ/ BBgAR3TOY3mg+C4AAAAASUVORK5CYII=" alt="Switchboard Icon">
            Switchboard
            <span class="spinner" style="display: none;"><i class="fa fa-spinner fa-spin"></i></span>
          </h1>
          <div class="messages micro">
            % for m in messages:
            <div class="message ${m['status']}" data-timeout="10000">
              <button type="button" class="close" data-dismiss="alert">&times;</button>
              ${m['message']}
            </div>
            % endfor
          </div>
          <div class="toolbar" data-sort="${sorted_by}">
            <a class="btn btn-success add-switch" href="#add-switch"><i class="fa fa-plus"></i> Add a Switch</a>

            <input type="search" placeholder="search">

            <ul class="sort">
              <li class="date_created">
                <a href="?by=${sort_by_key('date_created', sorted_by)}">Date Created</a>
              </li>
              <li class="date_modified">
                <a href="?by=${sort_by_key('date_modified', sorted_by)}">Date Modified</a>
              </li>
              <li class="label">
                <a href="?by=${sort_by_key('label', sorted_by)}">Label</a>
              </li>
            </ul>
          </div>
        </header>
        <div class="switches ${'empty' if not switches else ''}">
          % for switch in switches:
          <div id="id_${switch['key']}" class="switch" data-switch-key="${switch['key']}" data-switch-label="${switch.get('label', '')}" data-switch-description="${switch.get('description', '')}" data-switch-status="${switch['status']}">
            <div class="status">
              <label for="status_${switch['key']}">Status</label>
              <select name="status_${switch['key']}">
                <option value="1" ${'selected' if switch['status'] == 1 else ''}>Disabled for everyone</option>
                <option value="2" ${'selected' if switch['status'] == 2 else ''}>Active only for set conditions</option>
                <option value="4" ${'selected' if switch['status'] == 4 else ''}>Inherit from parent switch</option>
                <option value="3" ${'selected' if switch['status'] == 3 else ''}>Active for everyone</option>
              </select>
            </div>
            <div class="name">
              <h5 class="title">
                % if switch.get('label'):
                ${switch['label']}
                % else:
                ${switch['key'].title()}
                % endif
                <small class="command micro">(${switch['key']})</small>
                <div class="actions btn-group">
                  <a href="#edit-switch" class="btn btn-link edit" title="Edit Switch"><i class="fa fa-pencil"></i></a>
                  <a href="#delete-switch" class="btn btn-link delete" title="Delete Switch"><i class="fa fa-trash-o"></i></a>
                  <a href="#history-switch" class="btn btn-link history" title="View Switch History"><i class="fa fa-clock-o"></i></a>
                </div>
              </h5>
              <h6 class="timestamp micro">
                % if sorted_by.lstrip('-') == 'date_created':
                Created ${timesince(switch['date_created'])} ago
                % else:
                Last modified ${timesince(switch['date_modified'])} ago
                % endif
              </h6>
            </div>
            % if switch.get('description'):
            <div class="description">
              <p>${switch['description']}</p>
            </div>
            % endif
            <div class="metadata">
              <div class="micro conditions">
                % for group in switch.get('conditions', []):
                <div class="group">
                  <label>${group['label']}</label>
                  % for field, value, display, is_exclude in group['conditions']:
                  <span data-switch="${group['id']}" data-field="${field}" data-value="${value}" class="value">
                    <nobr>
                      % if is_exclude:
                      <strong>not</strong>
                      % endif
                      ${display}
                      <a href="#delete-condition" class="btn btn-link delete-condition" title="Delete this condition">
                        <i class="fa fa-times"></i>
                      </a>
                    </nobr>
                  </span>
                  % endfor
                </div>
                % endfor
              </div>
              <div class="add-condition"><a class="btn btn-success" href="#add-condition"><i class="fa fa-plus"></i> Add a Condition</a></div>
              <div class="conditions-form" style="display: none;"></div>
            </div>
          </div>
          % endfor
        </div>

        <div class="drawer"></div>

        <div class="no-switches" style="${'display: none' if switches else ''}">
          You do not have any switches yet. <a href="#add-switch" class="add-switch">Add the first one</a>.
        </div>

        <script type="text/x-handlebars-template" id="switchHistory">
          <div class="close-action"><i class="fa fa-times"></i></div>
          {{#if versions.length}}
          {{#groupByDate versions}}
          <div class="version">
            <div class="version-summary">{{summarize this}}</div>
            <div class="version-meta">{{#if username}}By {{username}}. {{/if}}At <time datetime="{{datestampFormat timestamp}}">{{timeFormat timestamp}}</time>.</div>
          </div>
          {{/groupByDate}}
          {{else}}
          <div class="no-history">
            <p>No history found.</p>
          </div>
          {{/if}}
        </script>

        <script type="text/x-handlebars-template" id="switchForm">
          <div class="field">
            <label for="label">Label</label>
            <input name="label" type="text" value="{{#if label}}{{label}}{{/if}}" placeholder="A descriptive name for this switch.">
          </div>
          <div class="field">
            <label for="key">Key</label>
            <input name="key" type="text" value="{{#if key}}{{key}}{{/if}}" placeholder="The key can be any valid JSON string.">
          </div>
          <div class="field">
            <label for="description">Description</label>
            <textarea name="description" placeholder="A brief description on what this switch accomplishes.">{{#if description}}{{description}}{{/if}}</textarea>
          </div>
          <div class="actions">
            <a data-action="{{#if add}}add{{else}}update{{/if}}" data-curkey="{{curkey}}" class="btn submit-switch primary-action" href="#submit-switch">{{#if add}}Add{{else}}Update{{/if}}</a>
            or <a href="#cancel" class="cancel secondary-action">cancel</a>
          </div>
        </script>

        <script type="text/x-handlebars-template" id="switchData">
          <div id="id_{{key}}" class="switch" data-switch-key="{{key}}" data-switch-label="{{label}}" data-switch-description="{{description}}" data-switch-status="{{status}}">
            <div class="status">
              <label for="status_{{key}}">Status</label>
              <select name="status_{{key}}">
                <option value="1" {{#ifToggled 1}}selected{{/ifToggled}}>Disabled for everyone</option>
                <option value="2" {{#ifToggled 2}}selected{{/ifToggled}}>Active only for set conditions</option>
                <option value="4" {{#ifToggled 4}}selected{{/ifToggled}}>Inherit from parent switch</option>
                <option value="3" {{#ifToggled 3}}selected{{/ifToggled}}>Active for everyone</option>
              </select>
            </div>

            <div class="name">
              <h5 class="title">
                {{label}} <small class="command micro">({{key}})</small>
                <div class="actions btn-group">
                  <a href="#edit-switch" class="edit btn-link btn" title="Edit Switch"><i class="fa fa-pencil"></i></a>
                  <a href="#delete-switch" class="delete btn-link btn" title="Delete Switch"><i class="fa fa-trash-o"></i></a>
                  <a href="#history-switch" class="btn btn-link history" title="View Switch History"><i class="fa fa-clock-o"></i></a>
                </div>
              </h5>
              <h6 class="timestamp micro">
                Created {{timeSince date_created}}
              </h6>
            </div>

            {{#if description}}
            <div class="description">
              <p>{{description}}</p>
            </div>
            {{/if}}

            <div class="metadata">
              <div class="micro conditions">
                {{#each conditions}}
                  <div class="group">
                    <label>{{label}}</label>
                    {{#each conditions}}
                      <span data-switch="{{../id}}" data-field="{{[0]}}" data-value="{{[1]}}" class="value">
                        <nobr>{{#if [3]}}<strong>not</strong> {{/if}}{{[2]}}
                          <a href="#delete-condition" class="btn btn-link delete-condition" title="Delete this condition">
                            <i class="fa fa-times"></i>
                          </a>
                        </nobr>
                      </span>
                    {{/each}}
                  </div>
                {{/each}}
              </div>

              <div class="add-condition"><a class="btn btn-success" href="#add-condition"><i class="fa fa-plus"></i> Add a condition</a></div>
              <div class="conditions-form" style="display: none;"></div>
            </div>
          </div>
        </script>

        <script type="text/x-handlebars-template" id="switchConditions">
          <select name="condition">
            <option></option>
            <%
              last_group = None
              loop_first = True
            %>
            % for id, group, field in all_conditions:
              % if group != last_group:
                % if not loop_first:
                  </optgroup>
                % endif
                <optgroup label="${group}">
                <%
                  last_group = group
                %>
              % endif

              <option value="${id},${field.name}">
                % if group != field.label:
                ${group}:
                % endif
                ${field.label}
              </option>
              % if loop_first:
                <% loop_first = False %>
              % endif
            % endfor
            </optgroup>
          </select>

          % for id, group, field in all_conditions:
          <div class="fields" data-path="${id}.${field.name}" style="display:none;">
            <form action="" method="get" data-switch="${id}" data-field="${field.name}">
              ${field.render(None)|n}
              <label><input type="checkbox" name="exclude" value="1"/> Exclude</label>
              <button type="submit" class="btn">Add</button>
              % if field.help_text:
                <div class="helptext">${field.help_text}</div>
              % endif
            </form>
          </div>
          % endfor
        </script>
      </div>
    </div>
    <script src="//cdnjs.cloudflare.com/ajax/libs/jquery/2.0.3/jquery.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/handlebars.js/1.3.0/handlebars.min.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/moment.js/2.5.1/moment.js"></script>
    <script type="text/javascript">
      /*!
       * string_score.js: String Scoring Algorithm 0.1.10
       *
       * http://joshaven.com/string_score
       * https://github.com/joshaven/string_score
       *
       * Copyright (C) 2009-2011 Joshaven Potter <yourtech@gmail.com>
       * Special thanks to all of the contributors listed here https://github.com/joshaven/string_score
       * MIT license: http://www.opensource.org/licenses/mit-license.php
       *
       * Date: Tue Mar 1 2011
      */
      String.prototype.score=function(m,s){if(this==m){return 1}if(m==""){return 0}var f=0,q=m.length,g=this,p=g.length,o,k,e=1,j;for(var d=0,r,n,h,a,b,l;d<q;++d){h=m.charAt(d);a=g.indexOf(h.toLowerCase());b=g.indexOf(h.toUpperCase());l=Math.min(a,b);n=(l>-1)?l:Math.max(a,b);if(n===-1){if(s){e+=1-s;continue}else{return 0}}else{r=0.1}if(g[n]===h){r+=0.1}if(n===0){r+=0.6;if(d===0){o=1}}else{if(g.charAt(n-1)===" "){r+=0.8}}g=g.substring(n+1,p);f+=r}k=f/q;j=((k*(q/p))+k)/2;j=j/e;if(o&&(j+0.15<1)){j+=0.15}return j};
    </script>
    <script type="text/javascript">
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
        Handlebars.registerHelper('summarize', function(version) {
          function isEmpty(obj) {
            return Object.keys(obj).length === 0;
          }
          var added, changed, deleted;
          if (version['delta']) {
            added = version['delta']['added'];
            changed = version['delta']['changed'];
            deleted = version['delta']['deleted'];
          }
          var summary = '';
          if (!isEmpty(added)) {
            summary = 'Switch added.';
          } else if (!isEmpty(changed)) {
            summary = 'Switch edited.';
            if (changed['status']) {
              var oldStatus = changed['status'][0],
                  newStatus = changed['status'][1],
                  statusLabel = [
                    null, // statuses are not 0-based
                    'Disabled',
                    'Selective',
                    'Global',
                    'Inherit'
                  ];
              summary = 'Status changed from <span class="changed status-label-' + oldStatus + '"><i class="fa fa-circle"></i> ' + statusLabel[oldStatus] + '</span>' +
                        ' to <span class="changed status-label-' + newStatus + '"><i class="fa fa-circle"></i> ' + statusLabel[newStatus] + '</span>.';
            } else if (changed['value']) {
                var oldValue = changed['value'][0],
                    newValue = changed['value'][1],
                    oldConditions = Object.keys(oldValue).join(', '),
                    newConditions = Object.keys(newValue).join(', ');
                summary = 'Conditions updated.';
                if (oldConditions) {
                  summary += ' Old conditions: <span class="changed">' + oldConditions + '</span>.';
                }
                if (newConditions) {
                  summary += ' New conditions: <span class="changed">' + newConditions + '</span>.';
                }
            } else {
              summary += ' Fields changed: <span class="changed">' + Object.keys(changed).join(', ') + '</span>.';
            }
          } else if (!isEmpty(deleted)) {
            summary = 'Switch deleted.';
          }
          return new Handlebars.SafeString(summary);
        });
        Handlebars.registerHelper('timeSince', function(date) {
          return moment(date).fromNow();
        });
        Handlebars.registerHelper('datestampFormat', function(date) {
          return moment(date).format();
        });
        Handlebars.registerHelper('dateFormat', function(date) {
          return moment(date).format('MMMM Do YYYY, h:mm:ss a');
        });
        Handlebars.registerHelper('timeFormat', function(date) {
          return moment(date).format('h:mm:ss a');
        });
        Handlebars.registerHelper('groupByDate', function(versions, options) {
          function dateHeader(date) {
            return '<div class="version-date"><h6><i class="fa fa-calendar"></i> ' + moment(date).format('MMM Do, YYYY') + '</h6>';
          }
          function stripTime(version) {
            return new Date(version.timestamp).setHours(0, 0, 0, 0);
          }
          if (!versions || versions.length === 0) {
            return '';
          }
          var currentDate = stripTime(versions[0]),
              out = dateHeader(currentDate);
          for (var i = 0, l = versions.length; i < l; i++) {
            var version = versions[i],
                nextDate = stripTime(version);
            if (currentDate !== nextDate) {
              currentDate = nextDate;
              out += '</div>';
              out += dateHeader(currentDate);
            }
            out = out + options.fn(version);
          }
          return out + '</div>';
        });
        var templates = {};
        $('script[type*="template"]').each(function() {
          templates[this.id] = Handlebars.compile($(this).html());
        });

        // Events

        $('.add-switch', $sb).on('click', function(e) {
          e.preventDefault();
          var html = templates.switchForm({add: true});
          $drawer.trigger('drawer:show', [html, $(this)]);
        });

        $('.switches', $sb).on('click', '.edit', function(e) {
          e.preventDefault();
          var $row = $(this).parents('.switch:first');
          var html = templates.switchForm({
              add:           false,
              curkey:        $row.attr('data-switch-key'),
              key:           $row.attr('data-switch-key'),
              label:         $row.attr('data-switch-label'),
              description:   $row.attr('data-switch-description')
          });
          $drawer.trigger('drawer:show', [html, $row]);
        });

        $('.switches', $sb).on('click', '.delete', function(e) {
          e.preventDefault();
          var $row = $(this).parents('.switch:first');
          var $table = $row.parents('.switches:first');

          if (!confirm('Are you SURE you want to remove this switch?')) {
            return;
          }

          api(SWITCHBOARD.deleteSwitch, { key: $row.attr('data-switch-key') },
            function () {
              $row.remove();
              if (!$table.find('.switch').length) {
                $('.no-switches', $sb).show();
              }
            }
          );
        });

        $('.switches', $sb).on('click', '.history', function(e) {
          e.preventDefault();
          var $row = $(this).parents('.switch:first');
          $.getJSON(SWITCHBOARD.history, { key: $row.attr('data-switch-key') }, function(data) {
            if (data.success) {
              var html = templates.switchHistory({ versions: data.data });
              $drawer.trigger('drawer:show', [html, $row]);
            } else {
              alert("Unable to retrieve the switch's history. Got: " + JSON.stringify(data));
            }
          });
        });

        $('.switches', $sb).on('change', '.status select', function(e) {
          e.preventDefault();
          var $row = $(this).parents('.switch:first');
          var $el = $(this);
          var status = parseInt($el.val(), 10);

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
                $row.attr('data-switch-status', swtch.status);
                if ($.isArray(swtch.conditions) && swtch.conditions.length < 1 && swtch.status === 2) {
                  swtch.status = 3;
                }
              }
            }
          );
        });

        $('.switches', $sb).on('click', '.add-condition a', function(e) {
          e.preventDefault();
          var $form = $(this).parents('.metadata:first').find('.conditions-form:first');

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
            parents('.switch:first').
            find('div.fields').hide();

          $(this).
            parents('.switch:first').
            find('div[data-path="' + field[0] + '.' + field[1] + '"]').show();
        });

        $('.switches', $sb).on('submit', '.conditions-form form', function(e) {
          e.preventDefault();
          var $form = $(this);

          var data = {
            key: $form.parents('.switch:first').attr('data-switch-key'),
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
            $('.switches .switch[data-switch-key="' + data.key + '"]', $sb).replaceWith(result);
          });
        });

        $('.switches', $sb).on('click', '.conditions .delete-condition', function(e) {
          e.preventDefault();

          var $el = $(this).parents('span:first');

          var data = {
            key:   $el.parents('.switch:first').attr('data-switch-key'),
            id:    $el.attr('data-switch'),
            field: $el.attr('data-field'),
            value: $el.attr('data-value')
          };

          api(SWITCHBOARD.delCondition, data, function (swtch) {
            var result = templates.switchData(swtch);
            $('.switches .switch[data-switch-key="' + data.key + '"]').replaceWith(result);
          });
        });

        $drawer.on('drawer:show', function(e, html, $parent) {
          var newTop;
          if ($parent.parents('.page-header').length) {
            var $header = $parent.parents('.page-header');
            newTop = $header.offset().top + $header.outerHeight() - 1; // don't include border
            $drawer.addClass('header');
          } else {
            newTop = $parent.offset().top;
            $drawer.removeClass('header');
          }
          $drawer.css('top', newTop + 'px');
          $('.switch', $sb).addClass('overlayed');
          $drawer.html(html).show();
          if ($drawer.children('input')) {
            $drawer.children('input:first').focus();
          }
        });

        $drawer.on('drawer:hide', function(e) {
          e.preventDefault();
          $('.switch', $sb).removeClass('overlayed');
          $drawer.hide();
        });

        $drawer.on('click', '.cancel', function(e) {
          e.preventDefault();
          $drawer.trigger('drawer:hide');
        });

        $(document).on('keyup', function(e) {
          if (e.keyCode === 27) { $drawer.trigger('drawer:hide'); }
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
                if ($('.switches .switch', $sb).length === 0) {
                  $('.switches', $sb).html(result);
                  $('.switches', $sb).removeClass('empty');
                  $('.no-switches', $sb).hide();
                } else {
                  $('.switches .switch:last', $sb).after(result);
                }

                $drawer.trigger('drawer:hide');
              } else {
                $('.switches .switch[data-switch-key="' + curkey + '"]', $sb).replaceWith(result);
                $drawer.trigger('drawer:hide');
              }
              //$(result).click();
            }
          );
        });

        $drawer.on('click', '.close-action', function(e) {
          e.preventDefault();
          $drawer.trigger('drawer:hide');
        });

        $('input[type=search]').keyup(function () {
          var query = $(this).val();
          $('.switches .switch', $sb).removeClass('hidden');
          if (!query) {
            return;
          }
          $('.switches .switch', $sb).each(function (_, el) {
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

        function closer($message) {
          function slideComplete() {
            $(this).removeClass('active');
          }
          function fadeComplete() {
            $(this).slideUp(100, slideComplete);
          }
          $message.animate({ opacity: 0 }, {
            duration: 250,
            queue: false,
            complete: fadeComplete
          });
        }

        $('.message').each(function() {
          var $m = $(this),
              timeout = parseInt($m.attr('data-timeout'), 10);
          $m.addClass('active');
          $m.fadeIn(500);
          $('.close', $m).on('click', function() {
            closer($m);
          });
          if (timeout) {
            window.setTimeout(function() {
              closer($m);
            }, timeout);
          }
        });
      });
    </script>
  </body>
</html>
