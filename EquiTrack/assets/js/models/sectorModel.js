/*
* model: sectorModel
*
* Defines model for individual sector.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var sectorModel = Backbone.Model.extend({
    urlRoot: '/partners/sector',
    defaults: {
      sector_id: null,
      name: null, 
      description: null
    }
  });
  return sectorModel;
});
