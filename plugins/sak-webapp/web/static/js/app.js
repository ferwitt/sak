angular.module("app", []).controller("SakApp", function($scope, $http) {  
    $scope.message="Hello World" 

  $scope.plugins = []
  $http.get("/api/show/plugins")
  .then(function(response) {
    $scope.plugins = response.data;
  });

  $scope.cmd_path = []

  $scope.cmd_root = {}
  $http.get("/api/cmd/sak")
  .then(function(response) {
    $scope.cmd_root = response.data;
  });


} )
