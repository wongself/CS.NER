var entity;
var str;
var color_per = '#ffcdd2';
var color_loc = '#b3e5fc';
var color_org = '#fff9c4';
var color_none = 'transparent';

var type_task_checked_color = '#FFBF33';
var type_task_unchecked_color = '#FFE084';
var type_method_checked_color = '#B1BA24';
var type_method_unchecked_color = '#E4EA78';
var type_metric_checked_color = '#51C521';
var type_metric_unchecked_color = '#A9ED76';
var type_material_checked_color = '#1B9D96';
var type_material_unchecked_color = '#71E1C7';
var type_other_checked_color = '#1D6EB8';
var type_other_unchecked_color = '#71BBE7';
var type_generic_checked_color = '#AA52E5';
var type_generic_unchecked_color = '#DC97F7';
var type_none_color = 'transparent';

// $('#source_texarea').bind('keypress', function (event) {
//   if (event.keyCode == "13") {
//     $("#query_button").click();
//   }
// })

$('#source_texarea').bind('input propertychange', function () {
  var $text_src = $('#source_texarea')
  var $text_curr = $('#textarea_statistic_current')
  var $text_place = $('.textarea_placeholder_text')
  var max_length = 1000
  var text_src_length = $text_src.val().length
  var text_src_remain = parseInt(max_length - text_src_length)

  if (text_src_length > 0) {
    $text_place.css('display', 'none')
  } else {
    $text_place.css('display', 'block')
  }

  if (text_src_remain > 0) {
    $text_curr.html(text_src_length)
  } else {
    $text_curr.html(max_length)
    $text_src.val($text_src.val().substring(0, max_length))
  }
});

$(function () {
  $('#upload_doc_button').on('click', function () {
    $('#upload_doc_input').trigger('click');
  });

  $('#query_button').on('click', function () {
    console.log('test\n');
    var $text_src = $('#source_texarea')
    var $text_dst = $('#target_texarea')
    var csrftoken = $("[name=csrfmiddlewaretoken]").val();
    text_src = $text_src.val();

    if (text_src.length <= 0) {
      $('#source_check_modal').modal();
      return;
    }

    $('#query_button').html('\
      <span class="spinner-border spinner-border-sm mr-2" \
        role="status" aria-hidden="true">\
      </span>Recognizing...').addClass('disabled');

    $.ajax({
      type: 'post',
      url: './../entity_query/',
      data: {
        'input': text_src,
        csrfmiddlewaretoken: $('[name="csrfmiddlewaretoken"]').val()
      },
      dataType: 'json',
      success: function (ret) {
        console.log(ret['entity']);
        // $('#result').text(str)
        entity = ret['entity'];
        $text_dst.text(entity)
        $('#query_button').html('Recognize').removeClass('disabled');
      },
      error: function (ret) {
        console.log('error');
        console.log(ret);
        $('#query_button').html('Recognize').removeClass('disabled');
      }
    })
  })
})

function set_color(per, loc, org) {
  function showEntity(key, mode) {
    var color;
    if (mode == 'LOC') {
      color = loc;
    }
    else if (mode == 'PER') {
      color = per;
    }
    else if (mode == 'ORG') {
      color = org;
    }
    return '<span style="background-color: ' + color + '">' + key + '</span>';
  }

  if (entity == undefined || str == undefined) {
    return '';
  }

  var html = '';
  var tmp;
  for (var i = 0; i < str.length; i++) {
    if (entity[i] == 'B-LOC' || entity[i] == 'I-LOC') {
      tmp = showEntity(str[i], 'LOC');
    }
    else if (entity[i] == 'B-PER' || entity[i] == 'I-PER') {
      tmp = showEntity(str[i], 'PER');
    }
    else if (entity[i] == 'B-ORG' || entity[i] == 'I-ORG') {
      tmp = showEntity(str[i], 'ORG');
    }
    else {
      tmp = str[i];
    }
    html += tmp;
  }
  return html;
}

function change_color() {
  console.log('change_color')
  var loc, org, per;
  if ($("#checkbox_per").is(":checked"))
    per = color_per;
  else
    per = color_none;

  if ($("#checkbox_loc").is(":checked"))
    loc = color_loc;
  else
    loc = color_none;

  console.log($("#checkbox_org").is(":checked"))
  if ($("#checkbox_org").is(":checked"))
    org = color_org;
  else
    org = color_none;
  console.log(org)

  var result = document.getElementById('result');
  result.innerHTML = set_color(per, loc, org);
}



NProgress.configure({ showSpinner: false });
$(document).ajaxStart(function () {
  NProgress.start();
});

$(document).ajaxStop(function () {
  NProgress.done();
});