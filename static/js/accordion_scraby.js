// This probably doesn't work for now.
// $(document).ready(function(){
// 	// Add minus icon for collapse element which is open by default
// 	$(".collapse.show").each(function(){
// 		$(this).siblings(".card-header").find(".btn i").html("remove");
// 		$(this).prev(".card-header").addClass("highlight");
// 	});
	
// 	// Toggle plus minus icon on show hide of collapse element
// 	$(".collapse").on('show.bs.collapse', function(){
// 		$(this).parent().find(".card-header .btn i").html("remove");
// 	}).on('hide.bs.collapse', function(){
// 		$(this).parent().find(".card-header .btn i").html("add");
// 	});
	
// 	// Highlight open collapsed element 
// 	$(".card-header .btn").click(function(){
// 		$(".card-header").not($(this).parents()).removeClass("highlight");
// 		$(this).parents(".card-header").toggleClass("highlight");
// 	});
// });



function listing(lsts) {
	return `
	<ul class="listing">
	${lsts.map(function(lst) {
	return `<li>${lst}</li>`
	}).join('')}
	</ul>
	`
  };
  
  function listing(lsts) {
	return `
	<ul class="listing" type="1">
	${lsts.map(function(lst) {
	return `<li>${lst.map(function(lstng) {
		return `
		<ul class="nested_l" style="list-style-type:none">
		<li>${lstng}</li>
		</ul>`
		}).join('')}</li>`
	}).join('<br>')}
	</ul>
	`
  };

function success(data) {
	data.forEach(obj => {
		Object.entries(obj).forEach(([key, value]) => {
			$('.latestinfo').append(
				'<div class="card">' +
					'<div class="card-header" id="heading_' + key + '">' +
						'<input type="checkbox" name=" '+key+' "/>' +
						'<h2 class="clearfix mb-0"' +
							'<a class="btn btn-primary" role="button" data-toggle="collapse" data-target="#collapse_' + key + '" href="#collapse_' + key + '" aria-expanded="true" aria-controls="collapse_' + key + '" style="color: rgb(93, 129, 206);">' +
								key +
							'</a>' +
						'</h2>' +
					'</div>' +
					// '<div id="collapse_' + key + '" class="collapse show" aria-labelledby="heading_' + key + ' data-parent="#accordionDiv"">' +
					'<div id="collapse_' + key + '" class="collapse" aria-labelledby="heading_' + key + ' data-parent="#accordionDiv"">' +
						'<div class="card-body">' +
							listing(value) +
						'</div>' +
					'</div>' +
				'</div>'
			);
		});
	});
}


success(data1);

// var selected = [];
// $('#accordionDiv input:checked').each(function() {
// 	selected.push($(this).attr('name'));
// });

// function download(content, fileName, contentType) {
// 	var a = document.createElement("a");
// 	var file = new Blob([content], { type: contentType });
// 	a.href = URL.createObjectURL(file);
// 	a.download = fileName;
// 	a.click();
//    }
   
//    function onDownload() {
// 	   var final ={};
// 	   data1.forEach(obj => {
// 		   Object.entries(obj).forEach(([key, value]) => {
// 				final[key] = value[6][1]
// 		   });
// 		});
// 		download(JSON.stringify(final, null, 4), "json-file-name.json", "text/plain");
//    }
//    Copy
   
