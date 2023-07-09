var curtemp = new TimeSeries();
var settemp = new TimeSeries();
var settempm = new TimeSeries();
var settempp = new TimeSeries();
var pterm = new TimeSeries();
var iterm = new TimeSeries();
var dterm = new TimeSeries();
var pidval = new TimeSeries();
var avgpid = new TimeSeries();
var lastreqdone = 1;
var timeout;

function refreshinputs() {
  $.getJSON({
    url: "/allstats",
    timeout: 500,
    success: function (resp) {
      $("#inputSetTemp").val(resp.brewtemp);
      $("#inputSleep").val(resp.sleep_time);
      $("#inputWake").val(resp.wake_time);
      if (resp.is_awake == true) {
        $('#onoffSwich').addClass("btn-success");
        $('#onoffSwich').removeClass("btn-danger");
      } else {
        $('#onoffSwich').addClass("btn-danger");
        $('#onoffSwich').removeClass("btn-success");
      }
    }
  });
}

function resettimer() {
  clearTimeout(timeout);
  timeout = setTimeout(refreshinputs, 30000);
}

function onresize() {
  var h;
  if ($(window).height() * .50 > 450) {
    h = 450;
  } else {
    h = $(window).height() * .50;
  }
  $("#chart").attr("width", $("#fullrow").width() - 30);
  $("#chart").attr("height", h);
  $("#pidchart").attr("width", $("#fullrow").width() - 30);
  $("#pidchart").attr("height", h);

  if ($(document).width() < 600) {
    $("#toggleadv").html("Adv Stats");
  } else {
    $("#toggleadv").html("Advanced Stats");
  }
}

$(document).ready(function () {
  resettimer();
  $(this).keypress(resettimer);

  onresize();
  $(window).resize(onresize);

  createTimeline();
  refreshinputs();

  $('#onoffSwich').click(function () {
    if ($('#onoffSwich').hasClass('btn-success')) {
      $.get("/turnoff", function (data) {
        console.log("Response: " + data);
      });
    } else {
      $.get("/turnon", function (data) {
        console.log("Response: " + data);
      });
    }
  });

  $(".adv").hide();
  $("#toggleadv").click(function () {
    $(".adv").toggle();
  });

  $("#inputSetTemp").change(function () {
    $.post(
      "/brewtemp",
      { "settemp": $("#inputSetTemp").val() }
    );
    console.log($("#inputSetTemp").val());
  });

  $("#inputSleep").change(function () {
    $.post(
      "/setsleep",
      { "sleep": $("#inputSleep").val() }
    );
    console.log($("#inputSleep").val());
  });

  $("#inputWake").change(function () {
    $.post(
      "/setwake",
      { "wake": $("#inputWake").val() }
    );
    console.log($("#inputWake").val());
  });

  $("#btnTimerDisable").click(function () {
    $.post("/scheduler", { "scheduler": "off" });
    console.log("scheduler is off");
    $("#inputWake").hide();
    $("#labelWake").hide();
    $("#inputSleep").hide();
    $("#labelSleep").hide();
    $("#btnTimerDisable").hide();
    $("#btnTimerEnable").show();
  });

  $("#btnTimerEnable").click(function () {
    $.post("/scheduler", { "scheduler": "on" });
    console.log("scheduler is on");
    $("#inputWake").show();
    $("#labelWake").show();
    $("#inputSleep").show();
    $("#labelSleep").show();
    $("#btnTimerDisable").show();
    $("#btnTimerEnable").hide();
  });

});

setInterval(function () {
  if (lastreqdone == 1) {
    $.getJSON({
      url: "/allstats",
      timeout: 500,
      success: function (resp) {
        if (resp.sched_enabled == true) {
          $("#inputWake").show();
          $("#inputSleep").show();
          $("#btnTimerSet").show();
          $("#btnTimerDisable").show();
          $("#btnTimerEnable").hide();
        } else {
          $("#inputWake").hide();
          $("#inputSleep").hide();
          $("#btnTimerSet").hide();
          $("#btnTimerDisable").hide();
          $("#btnTimerEnable").show();
        }
        if (resp.is_awake == true) {
          $('#onoffSwich').addClass("btn-success");
          $('#onoffSwich').removeClass("btn-danger");
        } else {
          $('#onoffSwich').addClass("btn-danger");
          $('#onoffSwich').removeClass("btn-success");
        }
        if (resp.heating == true) {
          $("#heatStatus").removeClass("btn-dark");
          $("#heatStatus").addClass("btn-warning");
        } else {
          $("#heatStatus").removeClass("btn-warning");
          $("#heatStatus").addClass("btn-dark");
        }
        curtemp.append(new Date().getTime(), resp.temp);
        settemp.append(new Date().getTime(), resp.brewtemp);
        settempm.append(new Date().getTime(), resp.brewtemp - 4);
        settempp.append(new Date().getTime(), resp.brewtemp + 4);
        pterm.append(new Date().getTime(), resp.pterm);
        iterm.append(new Date().getTime(), resp.iterm);
        dterm.append(new Date().getTime(), resp.dterm);
        pidval.append(new Date().getTime(), resp.pidval);
        avgpid.append(new Date().getTime(), resp.avgpid);
        $("#curtemp").html(resp.temp.toFixed(2));
        $("#pterm").html(resp.pterm.toFixed(2));
        $("#iterm").html(resp.iterm.toFixed(2));
        $("#dterm").html(resp.dterm.toFixed(2));
        $("#pidval").html(resp.pidval.toFixed(2));
        $("#avgpid").html(resp.avgpid.toFixed(2));
      },
      complete: function () {
        lastreqdone = 1;
      }
    });
    lastreqdone = 0;
  }
}, 333);

function createTimeline() {
  var chart = new SmoothieChart({ grid: { verticalSections: 3 }, minValueScale: 1.05, maxValueScale: 1.05 });
  chart.addTimeSeries(settemp, { lineWidth: 1, strokeStyle: '#ffff00' });
  chart.addTimeSeries(settempm, { lineWidth: 1, strokeStyle: '#ffffff' });
  chart.addTimeSeries(settempp, { lineWidth: 1, strokeStyle: '#ffffff' });
  chart.addTimeSeries(curtemp, { lineWidth: 3, strokeStyle: '#ff0000' });
  chart.streamTo(document.getElementById("chart"), 500);

  var pidchart = new SmoothieChart({ grid: { verticalSections: 3 }, minValueScale: 1.05, maxValueScale: 1.05 });
  pidchart.addTimeSeries(pterm, { lineWidth: 2, strokeStyle: '#ff0000' });
  pidchart.addTimeSeries(iterm, { lineWidth: 2, strokeStyle: '#00ff00' });
  pidchart.addTimeSeries(dterm, { lineWidth: 2, strokeStyle: '#0000ff' });
  pidchart.addTimeSeries(pidval, { lineWidth: 2, strokeStyle: '#ffff00' });
  pidchart.addTimeSeries(avgpid, { lineWidth: 2, strokeStyle: '#ff00ff' });
  pidchart.streamTo(document.getElementById("pidchart"), 500);
}
