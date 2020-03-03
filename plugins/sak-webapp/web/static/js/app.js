app = angular.module("app", ['ui.sortable']);

app.controller("SakApp", function($scope, $http) {

  // Get list of all possible commands
  $scope.cmds = {}
  $scope.cmd_root = {};
  $http.get("/api/cmd/sak")
  .then(function(response) {
    $scope.cmd_root = response.data;
    function traverseCmdTree(cmd) {
        $scope.cmds[cmd.path] = cmd;
        cmd.subcmds.forEach(traverseCmdTree);
      }
    traverseCmdTree($scope.cmd_root);
    console.log($scope.cmds);
  });


  $scope.activeCmds = [];
  $scope.addCmdToActiveList = function(cmd) {
      time = new Date().getTime();
      $scope.activeCmds.push({id: time, response:null, cmd: cmd});
  };

  $scope.getActiveCmdById = function(cmdId) {
      ret = null;
      $scope.activeCmds.forEach(function(cmdEntry){
          if (cmdEntry.id === cmdId) {
              ret = cmdEntry.cmd;
          }
      });
      return ret;
  };

  $scope.removeActiveCmdById = function(cmdId) {
      entry = null;
      $scope.activeCmds.forEach(function(cmdEntry){
          if (cmdEntry.id === cmdId) {
              entry = cmdEntry;
          }
      });

      const index = $scope.activeCmds.indexOf(entry);
      if (index > -1) {
            $scope.activeCmds.splice(index, 1);
      }
  };

  $scope.runActiveCmdById = function(cmdId) {
      $scope.activeCmds.forEach(function(cmdEntry){
          if (cmdEntry.id === cmdId) {
              cmdEntry.response = "Running...";
              $http.get(cmdEntry.cmd.path).then(function(response) {
                  cmdEntry.response = response.data;
              });
          }
      });
  };

  $scope.getScope = function () {
      return $scope;
  }

})

app.directive("sakCmd", function(){
        return {
            restrict: "EA",
        scope: {
            id:'@',
            response:'@',
            get:'&',
            run:'&',
            close:'&',
            pscope:'&',
        },
        template: `<article class='card'>
                       <header>
                          {{ get().name }}
                          <button class="dangerous" ng-click=close()> close</button>
                       </header>
                       <footer>

                            <div ng-repeat="cmd in get().subcmds">
                                <button data-tooltip="{{cmd.helpmsg}}" class="tooltip-top" ng-click="pscope().addCmdToActiveList(cmd)">
                                    {{ cmd['name'] }}
                                </button>
                            </div>
                            <div ng-repeat="arg in get().args">
                                {{arg.name}}
                            </div>
                            <button ng-hide="!get().isCallable" class="tooltip-top" ng-click="run()">
                            RUN
                            </button>
                            {{ response }}
                       </footer>
                    </article>`
        };
});
