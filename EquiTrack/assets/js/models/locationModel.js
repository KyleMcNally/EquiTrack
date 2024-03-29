/*
* model: locationModel
*
* Defines model for individual sector.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var locationModel = Backbone.Model.extend({
    urlRoot: '/partners/location',
    defaults: {
      location_id: null
    }
  });
  return locationModel;
});
