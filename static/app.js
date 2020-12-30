function render_page($, page_info) {
  // Handles redirect from the oauth response page for the oauth flow.
  if (
    document.referrer != null &&
    document.referrer.includes("http://localhost:8000/oauth-response.html") &&
    page_info.item_id != null &&
    page_info.item_id.length > 0
  ) {
    $("#container").fadeOut("fast", function () {
      $("#item_id").text(page_info.item_id);
      $("#access_token").text(page_info.access_token);
      $("#intro").hide();
      $("#app, #steps").fadeIn("slow");
    });
  }

  var products = page_info.products;
  if (products.includes("assets")) {
    $("#assets").show();
  }
  // This functionality is only relevant for the UK Payment Initiation product.
  if (products.includes("payment_initiation")) {
    $(".payment_initiation").show();
    $.post("/api/create_link_token_for_payment", {}, function (data) {
      if (data.error != null) {
        $(".loading-indicator").hide();
        displayError($("#container"), data.error);
        return;
      }
      localStorage.setItem("link_token", data.link_token);
      // In the case of payment_initiation product, we need to wait for a
      // link token configured with payment initiation to be generated before
      // the Link handler can be initialized.
      handler = Plaid.create({
        token: data.link_token,
        onSuccess: function (public_token) {
          // This public token exchange step is not relevant for the
          // payment_initiation product and should be skipped.
          $.post(
            "/api/set_access_token",
            {
              public_token: public_token,
            },
            function (data) {
              $("#container").fadeOut("fast", function () {
                $("#item_id").text(data.item_id);
                $("#access_token").text(data.access_token);
                $("#intro").hide();
                $("#app, #steps").fadeIn("slow");
              });
            }
          );
        },
      });
      $("#link-btn").attr("disabled", false);
      $(".loading-indicator").hide();
    });
  
  } else {
    var handler = null;
    $.post("/api/create_link_token", {}, function (data) {
      if (data.error != null) {
        $(".loading-indicator").hide();
        displayError($("#container"), data.error);
        return;
      }
      localStorage.setItem("link_token", data.link_token);
      handler = Plaid.create({
        token: data.link_token,
        onSuccess: function (public_token) {
          $.post(
            "/api/set_access_token",
            {
              public_token: public_token,
            },
            function (data) {
              $("#container").fadeOut("fast", function () {
                $("#item_id").text(data.item_id);
                $("#access_token").text(data.access_token);
                $("#intro").hide();
                $("#app, #steps").fadeIn("slow");
              });
            }
          );
        },
      });
      $("#link-btn").attr("disabled", false);
      $(".loading-indicator").hide();
    });
  }

  var accessToken = qs("access_token");
  if (accessToken != null && accessToken !== "") {
    $.post(
      "/api/set_access_token",
      {
        access_token: accessToken,
      },
      function (data) {
        $("#container").fadeOut("fast", function () {
          $("#item_id").text(data.item_id);
          $("#access_token").text(accessToken);
          $("#intro").hide();
          $("#app, #steps").fadeIn("slow");
        });
      }
    );
  }

  $("#link-btn").on("click", function (e) {
    if (handler != null) {
      handler.open();
    }
  });

  $("#get-transactions-btn").on("click", function (e) {
    $.get("/api/transactions", function (data) {
      if (data.error != null && data.error.error_code != null) {
        // Format the error
        var errorHtml =
          '<div class="inner"><p>' +
          "<strong>" +
          data.error.error_code +
          ":</strong> " +
          (data.error.display_message == null
            ? data.error.error_message
            : data.error.display_message) +
          "</p></div>";

        if (data.error.error_code === "PRODUCT_NOT_READY") {
          // Add additional context for `PRODUCT_NOT_READY` errors
          errorHtml +=
            '<div class="inner"><p>Note: The PRODUCT_NOT_READY ' +
            "error is returned when a request to retrieve Transaction data " +
            'is made before Plaid finishes the <a href="https://plaid.com/' +
            'docs/quickstart/#transaction-data-with-webhooks">initial ' +
            "transaction pull.</a></p></div>";
        }
        // Render the error
        $("#get-transactions-data").slideUp(function () {
          $(this).slideUp(function () {
            $(this).html(errorHtml).slideDown();
          });
        });
        return;
      }

      window.location.href = "/transactions";
    });
  });

 
}
$.post("/api/info", {}, function (result) {
  render_page(jQuery, result);
});

function qs(key) {
  key = key.replace(/[*+?^$.\[\]{}()|\\\/]/g, "\\$&"); // escape RegEx meta chars
  var match = location.search.match(new RegExp("[?&]" + key + "=([^&]+)(&|$)"));
  return match && decodeURIComponent(match[1].replace(/\+/g, " "));
}

function displayError(element, error) {
  var html = `
<div class="alert alert-danger">
<p><strong>Error Code:</strong> ${error.error_code}</p>
<p><strong>Error Type:</strong> ${error.error_type}</p>
<p><strong>Error Message:</strong> ${
    error.display_message == null ? error.error_message : error.display_message
  }</p>
<div>Check out our <a href="https://plaid.com/docs/#errors-overview">errors documentation</a> for more information.</div>
</div>`;
  $(element).html(html).slideDown();
}

// Functionality for 'Apply Categories' button
$("body").on("click", "#apply-categories", function (e) {
  const matchingIDs = {};
  let transactions = document.querySelectorAll(".trans-selector");
  let length = transactions.length;

  for (let i = 0; i < length; i++) {
    let tempData = document.getElementById(transactions[i].id);
    if (tempData.value != "null") {
      matchingIDs[tempData.dataset.transid] = tempData.value;
    }
  }

  $.ajax({
    type: "POST",
    contentType: "application/json",
    data: JSON.stringify(matchingIDs),
    dataType: "json",
    url: "/apply-categories",
  })
    .done(function () {
      for (let i = 0; i < length; i++) {
        let tempData = document.getElementById(transactions[i].id);
        if (tempData.value != "null") {
          tempData.parentElement.parentElement.parentElement.remove();
        }
      }
    })
    .fail(function (error) {
      console.log(error);
    });
});

// if categorized click, show categorized transactions
$("#categorized").on("click", function (e) {
  e.preventDefault();
  let checked = document.getElementById("categorized");

  if (checked.checked == false) {
    window.location.href = "/transactions";
  } else {
    window.location.href = "/allTransactions";
  }
});

// handle filter-by on expense-report
$("#date-sort").submit(function (e) {
  e.preventDefault();
  let value = document.getElementById("selected-value").value;
  window.location.href = `/expense-report-${value}`;
});
