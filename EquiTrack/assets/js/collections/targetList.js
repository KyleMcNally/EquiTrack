/*
* collection: targetList
*
* Defines collection that holds all targets
* for the map page filter.
*/
define([
  'jquery',
  'underscore',
  'backbone',
  'targetModel'
], function($, _, Backbone, targetModel) {
  var targetList = Backbone.Collection.extend({
    initialize: function() {
      this.url = '/target';
      this.model = targetModel;
    }
  });
  return targetList;
});
