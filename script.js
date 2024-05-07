$(document).ready(function() {
    function updateStationInfo(line, station) {
        $.ajax({
            url: '/station/' + line + '/' + station,
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                var alewifeText = data.alewife_predictions.map(function(prediction) {
                    return prediction.departure_time;  // Extract the departure_time for each prediction
                }).join(", ");
                $('#' + station + '-alewife').text('Alewife: ' + alewifeText);

                var braintreeText = data.braintree_predictions.map(function(prediction) {
                    return prediction.departure_time;  // Extract the departure_time for each prediction
                }).join(", ");
                $('#' + station + '-braintree').text('Braintree: ' + braintreeText);

                var ashmontText = data.ashmont_predictions.map(function(prediction) {
                    return prediction.departure_time;  // Extract the departure_time for each prediction
                }).join(", ");
                $('#' + station + '-ashmont').text('Ashmont: ' + (ashmontText || "No predictions"));

                var mattapanText = data.mattapan_predictions.map(function(prediction) {
                    return prediction.departure_time;  // Extract the departure_time for each prediction
                }).join(", ");
                $('#' + station + '-mattapan').text('Mattapan: ' + (mattapanText || "No predictions"));
            },
            error: function(xhr, status, error) {
                $('#' + station + '-alewife').text('Alewife: Error loading data');
                $('#' + station + '-braintree').text('Braintree: Error loading data');
                $('#' + station + '-ashmont').text('Ashmont: Error loading data');
                $('#' + station + '-mattapan').text('Mattapan: Error loading data');
            }
        });
    }

    var stations = [
        "alewife", 
        "davis", 
        "Porter", 
        "Harvard", 
        "Central", 
        "Kendal", 
        "Charles", 
        "Park-Street", 
        "downtowncrossing", 
        "South-Station", 
        "Broadway", 
        "Andrew", 
        "JFK", 
        "North-Quincy", 
        "Wollaston", 
        "Quincy-Center", 
        "Quincy-Adams",
        "Braintree", 
        "Savin-Hill", 
        "Fields-Corner", 
        "Shawmut", 
        "Ashmont",
        "Cedar-Grove",
        "Butler",
        "Milton",
        "Central-Ave",
        "Valley-Rd",
        "Capen-St",
        "Mattapan"
    ];

    var line = 'red'; 

    stations.forEach(function(station) {
        updateStationInfo(line, station);
        setInterval(function() {
            updateStationInfo(line, station);
        }, 30000);
    });
});