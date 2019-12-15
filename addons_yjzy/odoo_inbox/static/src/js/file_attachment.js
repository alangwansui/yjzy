window.onload = function() {

    //Check File API support
    if (window.File && window.FileList && window.FileReader) {
        var filesInput = document.getElementsByClassName("image_src");
        console.log("filesInput>111111111111111111>>>>>>>>>>>>>", filesInput)

        for (j = 0; j < filesInput.length; j++) {
            filesInput[j].addEventListener("change", function(event) {
                console.log("addEventListener>>>>change>>>>>>>>>>>>")
                var files = event.target.files; //FileList object
                //var output = document.getElementById("result");
                //var parentele = event.target.parentNode;
                var parentele = event.target.parentNode.nextElementSibling;

                $(files).each(function(file) {
                    var self = this;
                    var reader = new FileReader();
                    reader.readAsDataURL(this);
                    reader.onload = function(e) {
                        var picFile = e.target;
                        var div = document.createElement("div");
                        console.log("????????????", self.type)
                        if (self.type.match('image')) {
                            div.innerHTML = "<span href='#' class='fa fa-times-circle'></span> <img class='thumbnail' src='" + picFile.result + "'" +
                                "title='" + self.name + "'/>";
                        } else if (self.type === 'application/vnd.ms-excel') {
                            div.innerHTML = "<span href='#' class='fa fa-times-circle'></span> <img class='thumbnail' src='/odoo_inbox/static/src/img/excel.png'" +
                                "title='" + self.name + "'/>";
                        } else if (self.type === 'application/pdf') {
                            div.innerHTML = "<span href='#' class='fa fa-times-circle'></span> <img class='thumbnail' src='/odoo_inbox/static/src/img/pdf.png'" +
                                "title='" + self.name + "'/>";
                        } else {
                            div.innerHTML = "<span href='#' class='fa fa-times-circle'></span> <img class='thumbnail' src='/odoo_inbox/static/src/img/zip.png'" +
                                "title='" + self.name + "'/>";
                        }
                        parentele.appendChild(div);
                        div.children[0].addEventListener("click", function(event) {
                            div.parentNode.removeChild(div);
                        });
                    };
                })
                // for (var i = 0; i < files.length; i++) {
                //     console.log('a____________', event.target.parentNode);
                //     var file = files[i];

                //     //Only pics
                //     // if(!file.type.match('image'))
                //     //   continue;

                //     var picReader = new FileReader();

                //     picReader.addEventListener("load", function(event) {

                //         var picFile = event.target;
                //         console.log('picFileeeeeeeeeeeeeeeee', picFile);
                //         // console.log('picFile.resultttttttttt', picFile.result);

                //         var div = document.createElement("div");
                //         if (file.type.match('image')) {
                //             div.innerHTML = "<img class='thumbnail' src='" + picFile.result + "'" +
                //                 "title='" + file.name + "'/> <span href='#' class='remove_pict'>X</span>";
                //         } else if (file.type.match('application/vnd.ms-excel')) {
                //             div.innerHTML = "<img class='thumbnail' src='/odoo_inbox/static/src/img/excel.png'" +
                //                 "title='" + file.name + "'/> <span href='#' class='remove_pict'>X</span>";
                //         } else if (file.type.match('application/pdf')) {
                //             div.innerHTML = "<img class='thumbnail' src='/odoo_inbox/static/src/img/pdf.png'" +
                //                 "title='" + file.name + "'/> <span href='#' class='remove_pict'>X</span>";
                //         } else {
                //             div.innerHTML = "<img class='thumbnail' src='/odoo_inbox/static/src/img/zip.png'" +
                //                 "title='" + file.name + "'/> <span href='#' class='remove_pict'>X</span>";
                //         }

                //         parentele.appendChild(div);
                //         div.children[1].addEventListener("click", function(event) {
                //             div.parentNode.removeChild(div);
                //         });

                //     });

                //     //Read the image
                //     picReader.readAsDataURL(file);
                // }

            });
        }
    } else {
        console.log("Your browser does not support File API");
    }
}