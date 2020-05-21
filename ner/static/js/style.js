var max_length = 5000
var target_original_jpredictions

var type_task_index = 5
var type_method_index = 7
var type_metric_index = 11
var type_material_index = 13
var type_other_index = 17
var type_generic_index = 19
var type_overlap_index = 35
var type_none_index = 1

// $('#source_texarea').bind('keypress', function (event) {
//   if (event.keyCode == "13") {
//     $("#query_button").click();
//   }
// })

$(function () {
  $('#source_texarea').val('')
  $('#target_texarea').html('')

  // Textarea discription
  $('#source_texarea').bind('input propertychange', function () {
    _undisplay_textarea_discription()
  })

  // Upload document
  $('#upload_doc_button').on('click', function () {
    $('#upload_doc_input').trigger('click')
  })

  $('#upload_doc_input').on('change', function (e) {
    _disable_submit_button()

    var file = e.target.files[0]
    if (file.size <= 0) {
      var $modal = $('#error_happened_modal #modal_error_content')
      $modal.text('No document available.')
      $('#error_happened_modal').modal();
      console.error('No document available.');
    }
    var fileReader = new FileReader()

    fileReader.onload = function () {
      var typedarray = new Uint8Array(this.result);
      _get_pdf_text(typedarray).then(function (text) {
        var substring = text.substring(0, max_length)
        $("#source_texarea").val(substring)
        $("#target_texarea").html(substring)
        _undisplay_textarea_discription()
        _ajax_submit(substring)
        _enable_submit_button()
      }, function (e) {
        alert('Upload broken, try another')
        console.error(e);
        _enable_submit_button()
      })
    };
    fileReader.readAsArrayBuffer(file);
  })

  // Export predictions
  $('#export_output_button').on('click', function () {
    if (target_original_jpredictions == null) {
      var $modal = $('#error_happened_modal #modal_error_content')
      $modal.text('No prediction available.')
      $('#error_happened_modal').modal();
      console.error('No prediction available.');
      return;
    }
    _export_jpredictions()
  })

  // Type checkbox
  $('.type_checkbox_group .btn').on('click', function (e) {
    // e.stopPropagation()
    // e.preventDefault()
    var re_checkbox = /type_checkbox_\w+/g;
    var class_list = String($(this).attr("class"))
    var is_active = class_list.includes('active')

    var type_class_color = 'type-color-' + class_list.match(re_checkbox)[0].slice(14)
    var type_class_none = type_class_color + '-none'
    var re_class_color = new RegExp(type_class_color, 'g')
    var re_class_none = new RegExp(type_class_none, 'g')

    // var type_badge_color = 'badge'
    // var type_badge_none = 'badge-none'
    // var re_badge_color = new RegExp(type_badge_color, 'g')
    // var re_badge_none = new RegExp(type_badge_none, 'g')

    var texarea_src_html = $('#target_texarea').html()
    // console.log(texarea_src_html)
    var texarea_dst_html
    if (is_active) {
      texarea_dst_html = texarea_src_html.replace(re_class_color, type_class_none)
      // texarea_dst_html = texarea_dst_html.replace(re_badge_color, type_badge_none)
    } else {
      texarea_dst_html = texarea_src_html.replace(re_class_none, type_class_color)
      // texarea_dst_html = texarea_dst_html.replace(re_badge_none, type_badge_color)
    }
    // console.log(texarea_dst_html)
    $('#target_texarea').html(texarea_dst_html)
  })

  // Recognize entities
  $('#query_button').on('click', function () {
    var $text_src = $('#source_texarea')
    var text_src = $text_src.val();

    if (text_src.length <= 0) {
      var $modal = $('#error_happened_modal #modal_error_content')
      $modal.text('No text or document available.')
      $('#error_happened_modal').modal();
      console.error('No text or document available.');
      return;
    }

    _disable_submit_button()
    _ajax_submit(text_src)
  })
})

function _ajax_submit(source) {
  $.ajax({
    type: 'post',
    url: './../entity_query/',
    data: {
      'source': source,
      csrfmiddlewaretoken: $('[name="csrfmiddlewaretoken"]').val()
    },
    dataType: 'json',
    success: function (ret) {
      // console.log(ret['jpredictions'])
      var jpredictions = ret['jpredictions']
      target_original_jpredictions = jpredictions
      target_texarea_text = _parse_jpredictions(jpredictions)
      $('#target_texarea').html('')
      $('#target_texarea').html(target_texarea_text)
      _enable_submit_button()
    },
    error: function (ret) {
      console.log('error: ' + ret);
      _enable_submit_button()
    }
  })
}

function _parse_jpredictions(jpredictions) {
  console.log('Start Parsing')
  // console.log(jpredictions)
  var target_texarea_text = ''
  $.each(jpredictions, function (index, doc) {
    var jtokens = doc['tokens']
    var jentities = doc['entities']
    var index_tokens_type = (new Array(jtokens.length)).fill(1)

    $.each(jentities, function (index, entity) {
      var etype = entity['type']
      var estart = entity['start']
      var eend = entity['end']
      for (let i = estart; i < eend; i++) {
        index_tokens_type[i] *= _get_type_index(etype);
      }
    })

    target_texarea_text += '<p><span>'
    console.log(index_tokens_type)
    $.each(jtokens, function (index, token) {
      var tokens_type_color = _get_type_color(index_tokens_type[index])
      var is_span = !index || index_tokens_type[index - 1] !== index_tokens_type[index]
      var is_before_overlap = index && (index_tokens_type[index] >= type_overlap_index && index_tokens_type[index - 1] < type_overlap_index)
      var is_after_overlap = !index || (index_tokens_type[index-1] >= type_overlap_index && index_tokens_type[index] < type_overlap_index)
      var is_badge = (tokens_type_color !== 'type-color-none') ? 'badge ' : ''

      target_texarea_text += (is_span && !is_before_overlap) ? '</span>' : ''
      target_texarea_text += (is_span && is_after_overlap) ? '<span class="' + is_badge + tokens_type_color + '">' : ''
      target_texarea_text += (_is_string_punctuation(token.substring(0, 1)) || !index) ? '' : ' '
      target_texarea_text += (is_span && is_before_overlap) ? '</span>' : ''
      target_texarea_text += (is_span && !is_after_overlap) ? '<span class="' + is_badge + tokens_type_color + '">' + token : token
    })
    target_texarea_text += '</span></p>'
  })
  // console.log(target_texarea_text)
  return target_texarea_text
}

function _get_pdf_text(typedarray) {
  var pdf = PDFJS.getDocument(typedarray)
  return pdf.then(function (pdf) {
    var maxPages = pdf.pdfInfo.numPages
    var countPromises = []
    // collecting all page promises
    for (var j = 1; j <= maxPages; j++) {
      var page = pdf.getPage(j)
      countPromises.push(page.then(function (page) {
        var textContent = page.getTextContent()
        return textContent.then(function (text) {
          return text.items.map(function (s) {
            return s.str
          }).join('')
        });
      }));
    }
    // Wait for all pages and join text
    return Promise.all(countPromises).then(function (texts) {
      return texts.join('')
    })
  })
}

function _get_type_index(type) {
  switch (type) {
    case 'Task':
      return type_task_index
    case 'Method':
      return type_method_index
    case 'Metric':
      return type_metric_index
    case 'Material':
      return type_material_index
    case 'OtherScientificTerm':
      return type_other_index
    case 'Generic':
      return type_generic_index
    default:
      return type_none_index
  }
}

function _get_type_color(index) {
  var type_index_array = _decomposition_quality_factor(index)
  if (type_index_array.length === 0) {
    return 'type-color-none'
  }

  var type_index_class = ''
  $.each(type_index_array, function (index, type) {
    if (index) {
      type_index_class += ' '
    }

    switch (type) {
      case type_task_index:
        type_index_class += 'type-color-task'
        break;
      case type_method_index:
        type_index_class += 'type-color-method'
        break;
      case type_metric_index:
        type_index_class += 'type-color-metric'
        break;
      case type_material_index:
        type_index_class += 'type-color-material'
        break;
      case type_other_index:
        type_index_class += 'type-color-other'
        break;
      case type_generic_index:
        type_index_class += 'type-color-generic'
        break;
      default:
        break;
    }
  })

  return type_index_class
}

function _decomposition_quality_factor(n) {
  var n_array = []
  for (var i = 5; i <= n; i++) {
    if (n % i == 0) {
      n_array.push(i)
      n = n / i
      i = 5
    }
  }
  return n_array
}

function _export_jpredictions() {
  var jexport = JSON.stringify(target_original_jpredictions)
  var blob = new Blob([jexport], { type: "text/plain;charset=utf-8" })
  var filename = 'Predictions of CS.NER ' + _generate_timestamp() + '.json'

  var url = window.URL || window.webkitURL
  link = url.createObjectURL(blob)
  var a = $("<a />")
  a.attr("download", filename)
  a.attr("href", link)
  $("body").append(a)
  a[0].click()
  $("body").remove(a)
}

function _generate_timestamp() {
  var curr_time = new Date().Format("yyyy-MM-dd hh_mm_ss")
  return curr_time
}

function _expand_digit(digit) {
  var digit_expanded
  if (digit >= 1 && digit <= 9) {
    digit_expanded = "0" + digit;
  }
  return digit_expanded
}

function _is_string_punctuation(substring) {
  var punctuation = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
  return punctuation.includes(substring)
}

// function _is_string_left_punctuation(substring) {
//   var left_bracket = '([{'
//   return left_bracket.includes(substring)
// }

function _undisplay_textarea_discription() {
  var $text_src = $('#source_texarea')
  var $text_dst = $('#target_texarea')
  var $text_curr = $('#textarea_statistic_current')
  var $text_src_place = $('#source_texarea_placeholder_text')
  var $text_dst_place = $('#target_texarea_placeholder_text')
  var text_src_length = $text_src.val().length
  var text_dst_length = $text_dst.text().length
  var text_src_remain = parseInt(max_length - text_src_length)

  if (text_src_length > 0) {
    $text_src_place.css('display', 'none')
    $text_dst_place.css('display', 'none')
  } else {
    $text_src_place.css('display', 'block')
    $text_dst_place.css('display', 'block')
  }

  if (text_src_remain > 0) {
    $text_curr.html(text_src_length)
  } else {
    $text_curr.html(max_length)
    $text_src.val($text_src.val().substring(0, max_length))
  }
}

function _enable_submit_button() {
  $('#query_button').html('Recognize').removeClass('disabled');
  $("#upload_doc_button").attr('disabled', false)
}

function _disable_submit_button() {
  $('#query_button').html('\
      <span class="spinner-border spinner-border-sm mr-2" \
        role="status" aria-hidden="true">\
      </span>Recognizing...').addClass('disabled')
  $("#upload_doc_button").attr('disabled', true)
}

Date.prototype.Format = function (fmt) {
  var o = {
    "M+": this.getMonth() + 1,
    "d+": this.getDate(),
    "h+": this.getHours(),
    "m+": this.getMinutes(),
    "s+": this.getSeconds(),
    "q+": Math.floor((this.getMonth() + 3) / 3),
    "S": this.getMilliseconds()
  };
  if (/(y+)/.test(fmt)) fmt = fmt.replace(RegExp.$1, (this.getFullYear() + "").substr(4 - RegExp.$1.length));
  for (var k in o)
    if (new RegExp("(" + k + ")").test(fmt)) fmt = fmt.replace(RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
  return fmt;
}

NProgress.configure({ showSpinner: false });

$(document).ajaxStart(function () {
  NProgress.start();
});

$(document).ajaxStop(function () {
  NProgress.done();
});

