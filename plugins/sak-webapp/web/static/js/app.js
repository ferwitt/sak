app = angular.module("app", ['ui.sortable', 'ui.grid', 'ngSanitize']);

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
  });


  $scope.activeCmds = [];
  $scope.addCmdToActiveList = function(cmd) {
      time = new Date().getTime();

      entry = {id: time, response:null, params:{}, cmd: cmd}
      var arrayLength = entry.cmd.args.length;
      for (var i = 0; i < arrayLength; i++) {
        arg = entry.cmd.args[i];
      }
      $scope.activeCmds.push(entry);
  };

  $scope.getActiveCmdById = function(cmdId) {
      entry = null;
      $scope.activeCmds.forEach(function(cmdEntry){
          if (cmdEntry.id === cmdId) {
              entry = cmdEntry;
          }
      });
      return entry;
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
              cmdEntry.response = {processing: true};
              $http.get(
                cmdEntry.cmd.path,
                {
                params: cmdEntry.params
                }
              ).then(function(response) {
                  cmdEntry.response = response.data;
              },
                function(response) {
                  cmdEntry.response = {error: true, status: 'Uknown error... :('};
                }
              );
          }
      });
  };

  $scope.getScope = function () {
      return $scope;
  }

})

app.directive('sakCmdArg',
  function ($compile) {
        return {
            restrict: "EA",
        scope: false,
        template: function(scope, attrs) {
          ret = `
          <div class="flex two">
            <label>{{arg.name}} :</label>
            <div>
              <div ng-if="!arg.choices.length">
                <label ng-if="arg.type == 'bool'">
                  <input type="checkbox" ng-model="get().params[arg.name]"/>
                  <span class="checkable"></span>
                </label>
                <input ng-if="arg.type == 'string'" type="text" ng-model="get().params[arg.name]"/>
                <input ng-if="arg.type == 'list'" type="text" ng-model="get().params[arg.name]"/>
                <input ng-if="arg.type == 'int'" type="number" ng-model="get().params[arg.name]">
              </div>
              <div ng-if="arg.choices.length">
                <select ng-model="get().params[arg.name]" ng-options="choice for choice in arg.choices">
                </select>
              </div>
            </div>
          </div>
          `;

          return ret
        }
        };
  });

app.directive('sakCmdResponse',
  function ($compile) {
        return {
            restrict: "EA",
        scope: false,
        template: function(scope, attrs) {
          ret = `
            <div ng-if="get().response.processing">
                Processing
            </div>

            <div ng-if="!get().response.error">
                <div ng-if="get().response.type == 'pd.DataFrame'">
                     <div ui-grid="{ data: get().response.result }" class="myGrid"></div>
                </div>
                <div ng-if="get().response.type == 'html'">
                    <div ng-bind-html="get().response.result"></div>
                </div>
                <div ng-if="get().response.type == 'png'">
                  <img src="data:image/png;base64, {{get().response.result}}" alt="It was supposed to be a graph" />
                </div>
                <div ng-if="get().response.type == 'string'">
                    {{ get().response.result }}
                </div>
            </div>
            <div ng-if="get().response.error">
                Something fishy happened: {{ get().response['status'] }}
            </div>
          `;

          return ret
        }
        };
  });

app.directive("sakCmd", function(){
        return {
            restrict: "EA",
        scope: {
            id:'@',
            get:'&',
            run:'&',
            close:'&',
            pscope:'&',
        },
        template: `<article class='card'>
                       <header>
                          {{ get().cmd.name }}
                          <div class="flex one three-600 five-1000">
                          <button ng-repeat="cmd in get().cmd.subcmds" data-tooltip="{{cmd.helpmsg}}" class="tooltip-top" ng-click="pscope().addCmdToActiveList(cmd)">
                              {{ cmd['name'] }}
                          </button>
                          </div>
                          <button class="dangerous" ng-click=close()> close</button>
                       </header>
                       <footer>
                            <div ng-hide="!get().cmd.isCallable">
                              <form novalidate >
                                  <div ng-repeat="arg in get().cmd.args">
                                    <sak-cmd-arg argname="{{arg.name}}" argtype="{{arg.type}}" getcmd="get()"/>
                                  </div>
                                  <button class="tooltip-top" ng-click="run()">
                                      RUN
                                  </button>
                               </form>
                            </div>
                            <sak-cmd-response/>
                       </footer>
                    </article>`
        };
});
