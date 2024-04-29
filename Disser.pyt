import arcpy
import math
import os

class Toolbox(object):
    def __init__(self):
        self.label =  "Reconstruction of watercourses"
        self.alias  = "Reconstruction_of_watercourses"
        self.tools = [Reconstruction_of_watercourses, Reconstruction_of_watershades] 

class Reconstruction_of_watercourses(object):
    def __init__(self):
        self.label       = "Reconstruction of watercourses"
        self.description = "Reconstruction of watercourses"

    def getParameterInfo(self):
        DEM_input = arcpy.Parameter(
            displayName="Input DEM",
            name="DEM_input",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        
        
        out_stream_links = arcpy.Parameter(
            displayName="Output Stream",
            name="out_stream_links",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Output")
        
        help_1 = arcpy.Parameter(
            displayName="help_1",
            name="help_1",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")  
        
        help_2 = arcpy.Parameter(
            displayName="help_2",
            name="help_2",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output") 
        

        parameters = [DEM_input, 
                      out_stream_links,
                      help_1, help_2]
        
        return parameters
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        DEM_input = parameters[0].valueAsText
        out_stream_links = parameters[1].valueAsText
        help_1  = parameters[2].valueAsText
        help_2  = parameters[3].valueAsText

        # Подготовительный этап. Установка параметров среды: экстент, маска, размер ячейки на основе данных с ЦМР
        arcpy.env.overwriteOutput = True
        arcpy.env.extent = DEM_input
        arcpy.env.snapRaster = DEM_input
        arcpy.env.cellSize = DEM_input
        cell_x = arcpy.GetRasterProperties_management(DEM_input, "CELLSIZEX").getOutput(0)
        cell_y = arcpy.GetRasterProperties_management(DEM_input, "CELLSIZEY").getOutput(0)
        cell_area = float(cell_x.replace(',','.')) * float(cell_y.replace(',','.'))  

        # Вычисление углов наклона
        arcpy.AddMessage('Reconstruction of watercourses')
        slope_degree = arcpy.sa.Slope(DEM_input, "DEGREE")
        slope_tangent = arcpy.sa.Times(slope_degree, 0.0174533)  

        # Построение тальвегов
        #Этап 1. Заполнение пустот
        DEM_fill = arcpy.sa.Fill(DEM_input)
        # Этап 2. Создание растра направлений стока
        flow_directions = arcpy.sa.FlowDirection(DEM_fill, "NORMAL", 'slope_degree')

        # Этап 3. Растр суммарного потока
        flow_accumulation = arcpy.sa.FlowAccumulation(flow_directions)

        #Этап 4. Вычисление порогового значения
        CEI = flow_accumulation * cell_area * slope_tangent
        initials = arcpy.sa.Con(CEI > 800, 1)

        #Этап 5. Определение порядкового номера водотока
        stream_number = arcpy.sa.StreamOrder(initials , flow_directions,"STRAHLER")

        #Этап 5. Реконструкция водотоков
        arcpy.sa.StreamToFeature(stream_number, flow_directions, "stream_links", "NO_SIMPLIFY")

        #Этап 6. Объединение водотоков одного порядка
        arcpy.Dissolve_management('stream_links', "stream_dissolve", ["grid_code"], "", "SINGLE_PART", "DISSOLVE_LINES")


        #Этап 7. Разделение водотоков по точка пересечения (разделение v-образных вершин)
        fc_list = []
        i = 1
        arcpy.management.Sort('stream_dissolve', "sort_stream_rang", [["grid_code", "DESCENDING"]])
        values = [i[0] for i in arcpy.da.SearchCursor('sort_stream_rang', "grid_code")]
        max_range = values[1]

        for i in range(max_range):
            rivers_temp = 'rivers_%s_order' % (i+1)
            query = '"grid_code" =' + str(i+2)
            query_i = '"grid_code" =' + str(i+1)
            arcpy.MakeFeatureLayer_management('stream_dissolve', "streams_selection", query)
            arcpy.MakeFeatureLayer_management('stream_dissolve', "streams_selection_i", query_i)
            arcpy.FeatureVerticesToPoints_management('streams_selection', "intersect_point", "BOTH_ENDS")
            arcpy.SplitLineAtPoint_management('streams_selection_i', 'intersect_point', rivers_temp)
            fc_list.append(rivers_temp)
            arcpy.Delete_management('intersect_point')

        arcpy.Merge_management(fc_list, "rivers_output")
        arcpy.Delete_management('streams_selection')
        arcpy.Delete_management('streams_selection_i')
        for fc in fc_list:
            arcpy.Delete_management(fc)

        #Этап 8. Объединение водотоков разного порядка
        out_stream_links = arcpy.Dissolve_management('rivers_output', out_stream_links, "", "", "MULTI_PART", "UNSPLIT_LINES")


class Reconstruction_of_watershades(object):
    def __init__(self):
        self.label       = "Reconstruction of watershades"
        self.description = "Reconstruction of watershades"

    def getParameterInfo(self):
        DEM_input = arcpy.Parameter(
            displayName="Input DEM",
            name="DEM_input",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        
        input_mask = arcpy.Parameter(
            displayName="Mask",
            name="input_mask",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        select_watercourses = arcpy.Parameter(
            displayName="Select Watercourses",
            name="select_watercourses",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")       
        
        coord_syst = arcpy.Parameter(
            displayName ="Coordinate System",
            name="coord_syst",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")
        
        snow_height = arcpy.Parameter(
            displayName="Snow height",
            name="snow_height",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input") 
        
        output_text = arcpy.Parameter(
            displayName="Resulting avalanche parameters",
            name="output_text",
            datatype="DETextfile",
            parameterType="Required",
            direction="Output")
        
        watershed_output = arcpy.Parameter(
            displayName="Start zone polygon (output)",
            name="watershed_output",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        
        tranzit_zone_polygon = arcpy.Parameter(
            displayName="Tranzit zone polygon (output)",
            name="tranzit_zone_polygon",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        
        runout_polygon = arcpy.Parameter(
            displayName="Runout zone polygon (output)",
            name="runout_polygon",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        
        start_track = arcpy.Parameter(
            displayName="Start track (output)",
            name="start_track",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")

        tranzit_track = arcpy.Parameter(
            displayName="Tranzit track (output)",
            name="tranzit_track",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")
        
        runout_track  = arcpy.Parameter(
            displayName="Runout track (output)",
            name="runout_track",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")    

        help_1 = arcpy.Parameter(
            displayName="help_1",
            name="help_1",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output")  
        
        help_2 = arcpy.Parameter(
            displayName="help_2",
            name="help_2",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output") 
        
        help_3 = arcpy.Parameter(
            displayName="help_3",
            name="help_3",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output") 
        
        help_4 = arcpy.Parameter(
            displayName="help_4",
            name="help_4",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Output") 


        parameters = [DEM_input, input_mask, select_watercourses, coord_syst, snow_height,
                      output_text,
                      watershed_output, tranzit_zone_polygon, runout_polygon,
                      start_track, tranzit_track, runout_track,
                       
                       help_1, help_2, help_3, help_4
                      ]
        
        return parameters
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        DEM_input = parameters[0].valueAsText
        input_mask = parameters[1].valueAsText
        select_watercourses = parameters[2].valueAsText
        coord_syst = parameters[3].valueAsText
        snow_height = parameters[4].valueAsText

        output_text  = parameters[5].valueAsText

        watershed_output = parameters[6].valueAsText
        tranzit_zone_polygon = parameters[7].valueAsText
        runout_polygon = parameters[8].valueAsText
        
        start_track = parameters[9].valueAsText
        tranzit_track = parameters[10].valueAsText
        runout_track = parameters[11].valueAsText

        help_1 = parameters[12].valueAsText
        help_2 = parameters[13].valueAsText
        help_3 = parameters[14].valueAsText
        help_4 = parameters[15].valueAsText


        # Подготовительный этап. Установка параметров среды: экстент, маска, размер ячейки на основе данных с ЦМР
        arcpy.env.overwriteOutput = True
        arcpy.env.extent = DEM_input
        arcpy.env.snapRaster = DEM_input
        arcpy.env.cellSize = DEM_input
        arcpy.env.mask = input_mask
        cell_x = arcpy.GetRasterProperties_management(DEM_input, "CELLSIZEX").getOutput(0)
        cell_y = arcpy.GetRasterProperties_management(DEM_input, "CELLSIZEY").getOutput(0)
        cell_area = float(cell_x.replace(',','.')) * float(cell_y.replace(',','.'))  
        cell_x_f = float(cell_x.replace(',','.'))

        cell_p = math.ceil(cell_x_f)

        fc_list = arcpy.ListDatasets()
        for fc in fc_list:
            arcpy.Delete_management(fc)
        c_list = arcpy.ListFeatureClasses() 
        for i in c_list:
            arcpy.Delete_management(i)

        
# Этап 1. ПОИСК ТОЧКИ В 20 ГРАДУСОВ
        # 1.1. вычисление углов наклона в градусах
        slope_degree = arcpy.sa.Slope(DEM_input, "DEGREE")
        slope_tangent = arcpy.sa.Times(slope_degree, 0.0174533)  
        # 1.2. заполнение "дыр" в ЦМР
        DEM_fill = arcpy.sa.Fill(DEM_input)
        # 1.3. создание растра направлений стока
        flow_directions = arcpy.sa.FlowDirection(DEM_fill, "NORMAL", 'slope_degree')
        # 1.4. объединение участков выбранного водотока в единую линию (dissolve_stream - единая линия)
        arcpy.Dissolve_management(select_watercourses, "dissolve_stream", "", "", "MULTI_PART", "UNSPLIT_LINES")
        # 1.5. извлечение вершин из единой линии и дальнейший их подсчет (необходимо для того, чтобы установить границу возможного агрегирования)
        arcpy.management.FeatureVerticesToPoints('dissolve_stream', "dissolve_point", "ALL")
        arcpy.sa.ExtractValuesToPoints('dissolve_point', DEM_fill, "dissolve_point_rv")
        count_vertices = [i[0] for i in arcpy.da.SearchCursor('dissolve_point_rv', "RASTERVALU")]
        count_vertex = len(count_vertices)
        # 1.6. проверка корректности расположения начала и конца линии (если линия начинается в устье, то разворот)
        razn = count_vertices[0] - count_vertices[-1]
        if razn < 0:
            arcpy.edit.FlipLine('dissolve_stream')
            arcpy.AddMessage(' 1. Flip line')
        else:
            arcpy.AddMessage('1. No flip line')
        # 1.7. создание копии единой линии. Это необходимо для того, чтобы загустить вершины по размеру ячейки ЦМР 
        arcpy.management.Copy('dissolve_stream', "dens_copy")



        # 2.1.уплотнение исходной линии в соответствии с размером ячейки (необходимо для извлечения углов наклона из каждой ячейки)
        densify_line = arcpy.edit.Densify('dens_copy', "DISTANCE", cell_x)
        # 2.2 извлечение вершин уплотненной линии и присвоение им значения с растра углов наклона
        arcpy.management.FeatureVerticesToPoints(densify_line, "intersect_point", "ALL")
        arcpy.sa.ExtractValuesToPoints('intersect_point', slope_degree, "out_point") 

        # 2.3. создание списка вершин (в списке хранятся значения углов наклона)
        values_input = [i[0] for i in arcpy.da.SearchCursor('out_point', "RASTERVALU")]
        # 2.4. подготовка к циклу прохода по каждому элементу списка values
        boolval = True
        k = 1
        # 2.5. поиск точки перегиба 
        k = 1
        while True:
            # 2.5.1. создание двух списков из единого (в один записываются индексы всех точек, у которых значение угла наклона больше 20 градсов, в другой - меньше 20)
            points_upper = [values_input.index(i) for i in values_input if i > 20]
            points_below = [values_input.index(i) for i in values_input if i <= 20]
            # 2.5.3. агрегирование исходной ЦМР
            # 2.5.3.1. подготовка к агрегированию
            k = int(k+1)
            cell_agg = cell_p*k
            # 2.5.3.2. удаление переменных, полученных на прошлом этапе итерации (ИСПРАВИТЬ И ДОБАВИТЬ)
            del values_input[:]
            # 2.5.3.3. агрегирование исходной ЦМР 
            DEM_agg = arcpy.sa.Aggregate(DEM_fill, k, "MEAN")
            # 2.5.3.4. построение углов наклона по исходной цмр
            slope_degree_agg = arcpy.sa.Slope(DEM_agg, "DEGREE")
            # 2.5.3.5. копирование изначальной линии и ее загущение во столько же раз во сколько агрегируется ЦМР
            dens_copy_k = 'dens_copy_%s' %k
            arcpy.management.Copy('dissolve_stream', "dens_copy_k")
            arcpy.edit.Densify('dens_copy_k', "DISTANCE", cell_agg)
            # 2.5.3.6. извлечение вершин из уплотненной линии и присвоение им значений с растра углов наклона, полученног по агрегированной ЦМР
            arcpy.management.FeatureVerticesToPoints('dens_copy_k', "intersect_point_agg", "ALL")
            arcpy.sa.ExtractValuesToPoints('intersect_point_agg', slope_degree_agg, "out_point_agg")
            # 2.5.3.7. создание списка для следующей итерации и проверка его длины (количество элементов не должно быть меньше исходного количества точек в линии)
            values_input = [i[0] for i in arcpy.da.SearchCursor('out_point_agg', "RASTERVALU")]
            values_len = int(len(values_input))
            
            # 2.5.4. обработка результатов агрегирования
            # 2.5.4.1. в результате агрегирования получаем два массива. В одном ищем первую точку, в другом последнюю
            if values_len == count_vertex:
                query_below = '"OBJECTID" = {0}'.format(points_below[0])
                query_upper = '"OBJECTID" = {0}'.format(points_upper[-1])
                if points_below[0] == 0:
                    arcpy.MakeFeatureLayer_management('out_point_agg', "split_point", query_upper)
                if points_upper[-1] == 0:
                    arcpy.MakeFeatureLayer_management('out_point_agg', "split_point", query_below)
                else:
                    arcpy.MakeFeatureLayer_management('out_point_agg', "below_point", query_below)
                    arcpy.MakeFeatureLayer_management('out_point_agg', "upper_point", query_upper)
                    merge_list = ['below_point', 'upper_point']
                    arcpy.Merge_management(merge_list, "point_select_1")
                    arcpy.MakeFeatureLayer_management('point_select_1', "split_point")


                arcpy.management.Copy('dissolve_stream', "dens_copy_1")
                arcpy.management.SplitLineAtPoint('dens_copy_1', 'split_point', "split_lines_3", "5 Meters")  
                if points_below[0] == 0:
                    query_line = '"OBJECTID" = 1'
                else:
                    query_line = '"OBJECTID" = 2'
                arcpy.MakeFeatureLayer_management('split_lines_3', "select_line", query_line)              

  # 2.5.5.обработка выбранной линии
                # 2.5.5.1. добавление атрибута геометрии (длины)
                arcpy.management.AddGeometryAttributes('select_line', "LENGTH","METERS")
                values_len_line = [i[0] for i in arcpy.da.SearchCursor('select_line', "LENGTH")]
                value_len_line = values_len_line[0]
                # 2.5.5.2. уплотнение вершин линии до размера ячейки исходной цмр
                arcpy.edit.Densify('select_line', "DISTANCE", cell_p)
                arcpy.management.FeatureVerticesToPoints('select_line', "point_select_line", "ALL")
                # 2.5.5.3. извлечение значений углов наклона в каждой точке
                arcpy.sa.ExtractValuesToPoints('point_select_line', slope_degree, "select_point_value_slope")
                values_slope = [i[0] for i in arcpy.da.SearchCursor('select_point_value_slope', "RASTERVALU")]
                # 2.5.5.4. создание списка вершин, в которых значение угла наклона больше 20 градусов

                point_list_20 = []
                points_max_20 = [values_slope.index(i) for i in values_slope if i > 20]
                # 2.5.5.4. выбор и добавление в список точек перегиба (перехода между 20 градусами)
                for i in range(len(points_max_20)):
                    query_len_slope = '"OBJECTID" = {0}'.format(points_max_20[i])
                    point_extr_20 = 'point_%s_extr_20' % (i+1)
                    arcpy.MakeFeatureLayer_management('select_point_value_slope', point_extr_20, query_len_slope)
                    point_list_20.append(point_extr_20)
                # 2.5.5.5. объединение точек перегиба
                arcpy.Merge_management(point_list_20, "point_thr_ext_20")
                # 2.5.5.6. разрезание выбранной линии по точкам перегиба (в результате много коротких линий с углом больше 20 и есть длинные линии с углом меньше 20)
                arcpy.management.SplitLineAtPoint('select_line', 'point_thr_ext_20', "line_thr_ext_20", "1 Meters")
                arcpy.management.AddGeometryAttributes('line_thr_ext_20', "LENGTH","METERS")
                # 2.5.5.7. сортировка по длине (сначала будут линии с углом меньше 20 градусов)
                arcpy.management.Sort('line_thr_ext_20', "line_thr_ext_sort_20", [["LENGTH", "DESCENDING"]])
                values_slope_max_20 = [i[0] for i in arcpy.da.SearchCursor('line_thr_ext_sort_20', "LENGTH")]
                value_slope_max_20 = values_slope_max_20[0]
                percent_line_20 = value_slope_max_20*100/value_len_line
                # 2.5.5.7. есть два преобладающих отрезка
                if percent_line_20 >= 20:
                    query_line_20_25 = '"OBJECTID" = 1'
                    arcpy.MakeFeatureLayer_management('line_thr_ext_sort_20', "line_thr_min_20", query_line_20_25)
                    arcpy.FeatureVerticesToPoints_management('line_thr_min_20', "point_thr_start_end_20", "BOTH_ENDS")
                    arcpy.sa.ExtractValuesToPoints('point_thr_start_end_20', DEM_fill, "point_thr_start_end_height_20")
                    arcpy.management.Sort('point_thr_start_end_height_20', "point_thr_start_end_height_sort_20", [["RASTERVALU", "DESCENDING"]])
                    query_point_20 = '"OBJECTID" = 1'
                    arcpy.MakeFeatureLayer_management('point_thr_start_end_height_sort_20', "point_zone_20", query_point_20)
                    arcpy.AddMessage('2. Tranzit zone line ok')

                if percent_line_20 < 20:
                    arcpy.management.AddGeometryAttributes('point_select_line', "POINT_X_Y_Z_M","METERS")
                    arcpy.sa.ExtractValuesToPoints('point_select_line', DEM_fill, "select_point_value")
                    flds = ['POINT_X', 'POINT_Y', 'RASTERVALU']
                    # 2.5.5.8.2. создание списков для каждой координаты
                    px = [i[0] for i in arcpy.da.SearchCursor('select_point_value', "POINT_X")][0]
                    py = [i[0] for i in arcpy.da.SearchCursor('select_point_value', "POINT_Y")][0]
                    pz = [i[0] for i in arcpy.da.SearchCursor('select_point_value', "RASTERVALU")][0]
                    angle = []
                    cnt = 0
                    with arcpy.da.SearchCursor('select_point_value', flds) as cursor:
                        for i in cursor:
                            # 2.5.5.8.3. проход по каждой точке (за исключением первой и второй от вершины)
                            if cnt >= 2:
                                # 2.5.5.8.4. извлечение двух точек - первой и итерируемой
                                selection_query = '"OBJECTID" = {0} OR "OBJECTID" = {1}'.format(0, cnt)
                                # 2.5.5.8.5. добавление точек на новый слой
                                arcpy.MakeFeatureLayer_management('select_point_value', "current_points", selection_query)
                                # 2.5.5.8.6. разрезание линии по двум точкам
                                arcpy.management.SplitLineAtPoint('select_line', 'current_points', "splitted_fclass", "1 Meters")
                                line_length = 0
                                # 2.5.5.8.7. поиск тангенса угла между двумя точками
                                for row in arcpy.da.SearchCursor('splitted_fclass', ["SHAPE@", "SHAPE@LENGTH"]):
                                    if (row[0].firstPoint.X == px and row[0].firstPoint.Y == py):
                                        line_length = row[1]                                    
                                        break
                                if (line_length != 0):
                                    tg_A = (pz - i[2]) / line_length
                                    angle.append(math.degrees(math.atan(tg_A)))
                                    arcpy.Delete_management('current_points')
                                    arcpy.Delete_management('splitted_fclass')
                                else:
                                    arcpy.AddMessage('Zero Division Error')
                                    arcpy.Delete_management('current_points')
                                    arcpy.Delete_management('splitted_fclass')
                            cnt += 1
                    point_max_len = len([angle.index(i) for i in angle if i <= 20])
                    if point_max_len == 0:
                        point_max = [angle.index(i) for i in angle][-1]
                        query_len_slope_2 = '"OBJECTID" = {0}'.format(point_max)
                    else:
                        point_max = [angle.index(i) for i in angle if i <= 20][1]
                        query_len_slope_2 = '"OBJECTID" = {0}'.format(point_max)
                    arcpy.MakeFeatureLayer_management('select_point_value_slope', "point_zone_20", query_len_slope_2)
                    arcpy.AddMessage('2. Tranzit zone line ok')

                arcpy.management.Copy('dissolve_stream', "dens_copy_2")
                arcpy.management.SplitLineAtPoint('dens_copy_2', 'point_zone_20', "tranzit_end", "1 Meters")  

                # 2.5.5.8.9. поиск верхней из двух линий
                with arcpy.da.SearchCursor('dissolve_stream', 'SHAPE@') as cursor:
                    for row in cursor:
                        coords_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        break
                objval_1 = 0
                with arcpy.da.SearchCursor('tranzit_end', ['SHAPE@', 'OID@']) as cursor:
                    for row in cursor:
                        split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        if (coords_start == split_start):
                            objval_1 = row[1]
                            break
                query_line_1 = '"OBJECTID" = {0}'.format(objval_1)
                arcpy.MakeFeatureLayer_management('tranzit_end', "aval_tranz_zone", query_line_1)

                with arcpy.da.SearchCursor('dissolve_stream', 'SHAPE@') as cursor:
                    for row in cursor:
                        coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        break
                objval_2 = 0
                with arcpy.da.SearchCursor('tranzit_end', ['SHAPE@', 'OID@']) as cursor:
                    for row in cursor:
                        split_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        if (coords_end == split_end):
                            objval_2 = row[1]
                            break
                query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
                arcpy.MakeFeatureLayer_management('tranzit_end', "runout_line_no_angle", query_line_2)
                break




# ПОИСК ВО3МОЖНОГО ИСКРИВЛЕНИЯ ЛИНИИ БОЛЬШЕ ЧЕМ НА 30 ГРАДУСОВ
        # уплотняем зону осаждения по размеру ячейки
        arcpy.edit.Densify('runout_line_no_angle', "DISTANCE", cell_p)
        # превращаем линию в точки
        arcpy.management.FeatureVerticesToPoints('runout_line_no_angle', "point_runout_line_no_angle", "ALL")
        # добавляем координаты x и y
        arcpy.management.AddGeometryAttributes('point_runout_line_no_angle', "POINT_X_Y_Z_M","METERS")
        flds = ['POINT_X', 'POINT_Y']
        # 2.5.5.8.2. создание списков для каждой координаты
        px = [i[0] for i in arcpy.da.SearchCursor('point_runout_line_no_angle', "POINT_X")]
        py = [i[0] for i in arcpy.da.SearchCursor('point_runout_line_no_angle', "POINT_Y")]
        angle_r = []
        tan_threshol = 30
        # начинаем проходить по каждой точке и искать дирекционный угол на следующую точку
        for i in range(len(px) - 1):
            ro_x = abs(px[i] - px[i+1])
            ro_y = abs(py[i] - py[i+1])
            razn_x = px[i] - px[i+1]
            razn_y = py[i] - py[i+1]
            if razn_x == 0:
                angle_i = 0
            if razn_y == 0:
                angle_i = 90
            if razn_x > 0 and razn_y > 0:
                tan_a = ro_x/ro_y
                angle_i = math.degrees(math.atan(tan_a)) + 180
            if razn_x > 0 and razn_y < 0:
                tan_a = ro_x/ro_y
                angle_i = 360 - math.degrees(math.atan(tan_a))
            if razn_x < 0 and razn_y > 0:
                tan_a = ro_x/ro_y
                angle_i = 180 - math.degrees(math.atan(tan_a))
            if razn_x < 0 and razn_y < 0:
                tan_a = ro_x/ro_y
                angle_i = math.degrees(math.atan(tan_a))
            angle_r.append(angle_i)
        
        angle_thresh = []
        angle_thresh_id = []
        angle_all = []

        for k in range(len(angle_r) - 1):
            razn_angl = abs(angle_r[k] - angle_r[k+1])
            if razn_angl>= tan_threshol:
                angle_thresh_id.append(k)
                angle_thresh.append(razn_angl)
            
            
        if len(angle_thresh) != 0:
            query_point_30 = '"OBJECTID" = {0}'.format(angle_thresh_id[0]+1)
            arcpy.MakeFeatureLayer_management('point_runout_line_no_angle', "runout_zone_point_30",query_point_30)
            arcpy.management.SplitLineAtPoint('runout_line_no_angle', 'runout_zone_point_30', "tranzit_end_30", "1 Meters")
            arcpy.management.AddGeometryAttributes('tranzit_end_30', "LENGTH","METERS")
            len_runout_after_30_degree = [i[0] for i in arcpy.da.SearchCursor('tranzit_end_30', "LENGTH")][-1]
            arcpy.MakeFeatureLayer_management('runout_zone_point_30', "30_degree")
            arcpy.MakeFeatureLayer_management('runout_zone_point_30', "30_degree_wsh")
            arcpy.MakeFeatureLayer_management('point_zone_20', "20_degree")
            point_list_interest_point = ['20_degree','25_degree', '30_degree']
        else:
            arcpy.MakeFeatureLayer_management('point_zone_20', "20_degree")
            point_list_interest_point = ['20_degree','25_degree']
            arcpy.FeatureVerticesToPoints_management('runout_line_no_angle', "point_runout_zone_line", "BOTH_ENDS")
            query_point_30_end = '"OBJECTID" = 1'
            arcpy.MakeFeatureLayer_management('point_runout_zone_line', "30_degree_wsh", query_point_30_end)
        arcpy.AddMessage('3. Point 30 ok')
            


# ПОИСК ПОЛИГОНА 3ОНЫ 3АРОЖДЕНИЯ
        # Этап 3. Поиск полигона зоны зарождения
        # 3.1. поиск изогоны со значением 25 градусов
        # 3.1.1. создание искусственной поверхности из растра углов наклона (умноженной на значимое число)
        slope_100 = slope_degree * 100
        # 3.1.2. заполнение провалов в полученном растре (позволяет без агрегирования убрать небольшие локальные спрямления)
        Slope_fill = arcpy.sa.Fill(slope_100)
        # 3.1.3. переклассификация растра, необходима для создания целочисленного растра с углами больше 25 градусов и меньше 25 градусов
        remap = arcpy.sa.RemapRange([[0,2500,0],[2500,6000,1],[6000,9000,0]])
        slope_reclass = arcpy.sa.Reclassify(Slope_fill, "Value", remap, "NODATA")
        # 3.1.4. превращение растра в полигоны и отбор (оставляются только полигоны с углами наклона более25 градусов)
        arcpy.conversion.RasterToPolygon(slope_reclass, "slope_polygon", "NO_SIMPLIFY", "Value")
        query_slope = '"gridcode" = 1'
        # 3.1.5.превращение полигонов в линии
        arcpy.MakeFeatureLayer_management('slope_polygon', "slope_poly_25", query_slope)
        arcpy.management.PolygonToLine('slope_poly_25', "slope_line_25")
        # 3.1.6. добавление к линии атрибута геометрии для сортировки и исключения коротких линий
        arcpy.management.AddGeometryAttributes('slope_line_25', "LENGTH","METERS")
        arcpy.management.Sort('slope_line_25', "slope_line_25_sort", [["LENGTH", "DESCENDING"]])
        len_slope_max = [i[0] for i in arcpy.da.SearchCursor('slope_line_25_sort', "LENGTH")][0]
        len_threshold = len_slope_max * 10 / 100
        query_len = '"LENGTH" > {0}'.format(len_threshold)
        arcpy.MakeFeatureLayer_management('slope_line_25', "slope_line_25_len", query_len)
        arcpy.Dissolve_management('slope_line_25_len', "slope_line_dis", "", "", "MULTI_PART", "UNSPLIT_LINES")

        arcpy.analysis.Intersect(["slope_line_dis", 'aval_tranz_zone'] , "inter_slope_25_to_split", "", "", "POINT")
        arcpy.management.SplitLineAtPoint('aval_tranz_zone', 'inter_slope_25_to_split', "stream_25_line_split", "1 Meters")
        arcpy.management.AddGeometryAttributes('stream_25_line_split', "LENGTH","METERS")
        arcpy.management.Sort('stream_25_line_split', "stream_25_line_split_sort", [["LENGTH", "DESCENDING"]])
        query_most_len_line = '"OBJECTID" = 1'
        arcpy.MakeFeatureLayer_management('stream_25_line_split_sort',  "most_len_line", query_most_len_line)

        # 3.2.1. создание растра водораздела и конвертация его в вектор
        out_watershed_raster = arcpy.sa.Watershed(flow_directions, 'point_zone_20')
        arcpy.conversion.RasterToPolygon(out_watershed_raster, "out_watershed_polygon", "NO_SIMPLIFY", "Value")
        # 3.2.2. конвертация из полигона в линию
        arcpy.MakeFeatureLayer_management('out_watershed_polygon', "watershed_poly")
        arcpy.management.PolygonToLine('watershed_poly', "watershed_line")
        # 3.2.3. разрезание изогоны 25 градусов и линий водоразделов по точкам пересечения
        arcpy.FeatureVerticesToPoints_management('watershed_line', "watershed_vertex", "ALL")
        arcpy.management.SplitLineAtPoint('watershed_line', 'watershed_vertex', "watershed_line_split_vertex", "1 Meters")
        arcpy.FeatureVerticesToPoints_management('slope_line_dis', "slope_layer_inter_vertex", "ALL")
        arcpy.management.SplitLineAtPoint('slope_line_dis', 'slope_layer_inter_vertex', "slope_layer_split_vertex", "1 Meters")
        arcpy.analysis.Intersect(['slope_layer_split_vertex', 'watershed_line_split_vertex'], "point_output_split_poly", "", "", "POINT")
        arcpy.management.SplitLineAtPoint('slope_layer_split_vertex', 'point_output_split_poly', "slope_layer_inter_split", "1 Meters")
        arcpy.management.SplitLineAtPoint('watershed_line_split_vertex', 'point_output_split_poly', "watershed_line_split", "1 Meters")
        # 3.2.4. сохранение двух линий на один слой
        merge_list_watershed = ["slope_layer_inter_split", "watershed_line_split"]
        arcpy.Merge_management(merge_list_watershed, "watershed_line_25")
        # 3.2.5. создание полигонов из линий
        arcpy.management.FeatureToPolygon('watershed_line_25', "water_polygon_all")
        # 3.2.5. поиск и сохранение полигона, пересекающего тальвег

        arcpy.MakeFeatureLayer_management('water_polygon_all',  "water_polygon_all_fl")
        arcpy.management.SelectLayerByLocation('water_polygon_all_fl', "INTERSECT", 'most_len_line')
        arcpy.MakeFeatureLayer_management('water_polygon_all_fl', "watershed_intersect")
        arcpy.management.AddGeometryAttributes('watershed_intersect', "AREA", "", "SQUARE_METERS")
        arcpy.management.Sort('watershed_intersect', "watershed_intersect_sort", [["POLY_AREA", "DESCENDING"]])
        query_area_poly = '"OBJECTID" = 1'
        watershed_output = arcpy.MakeFeatureLayer_management('watershed_intersect_sort', watershed_output, query_area_poly)




# ПОИСК ТОЧКИ 25 ГРАДУСОВ
        # Разворачиваем линию так, чтобы счет шел снизу вверх, а не сверху вниз
        aval_tranz_zone_flip = arcpy.edit.FlipLine('aval_tranz_zone')
        # Ищем пересечения развернутой линии и полигона водораздела
        arcpy.analysis.Intersect([watershed_output, aval_tranz_zone_flip] , "intersect_point_slope_25", "", "", "POINT")
        # результатом поиска будут мультиточки, поэтому ищем просто точки
        arcpy.management.MultipartToSinglepart('intersect_point_slope_25', "intersect_point_25_sing")
        # к развернутой линии добавляем параметр длины для того, чтобы узнать суммарную длину зоны транзита и зоны зарождения
        arcpy.management.AddGeometryAttributes(aval_tranz_zone_flip, "LENGTH","METERS")
        len_all_line = [i[0] for i in arcpy.da.SearchCursor(aval_tranz_zone_flip, "LENGTH")][0]
        # задаем параметр процента длины от общей длины
        len_treshold_line = len_all_line * 20 / 100
        point_list = []
        # делаем список из id точек
        inter_point_1 = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "OBJECTID")]
        inter_point =  []

        arcpy.management.AddGeometryAttributes('intersect_point_25_sing', "POINT_X_Y_Z_M","METERS")
        px_i_25 = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "POINT_X")][-1]
        py_i_25 = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "POINT_Y")][-1]

        arcpy.FeatureVerticesToPoints_management(aval_tranz_zone_flip, "start_end_point_fl", "BOTH_ENDS")
        arcpy.management.AddGeometryAttributes('start_end_point_fl', "POINT_X_Y_Z_M","METERS")
        px_af = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "POINT_X")][-1]
        py_af = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "POINT_Y")][-1]

        if (px_i_25 != px_af and py_i_25 != py_af):
            inter_point = inter_point_1
        else:
            for i in range (len(inter_point_1)-1):
                inter_point.append(inter_point_1[i])


        if len(inter_point) == 1:
            query_point_25 = '"OBJECTID" = 1'
            arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "point_25_degree_end", query_point_25)
            arcpy.management.SplitLineAtPoint('dissolve_stream', 'point_25_degree_end', "line_25_degree", "1 Meters")
            arcpy.MakeFeatureLayer_management('line_25_degree', "line_to_wsh")
        else:
            # начинаем проходить по списку 
            for i in range(len(inter_point)):
                point_i = 'point_i_%s' % (i+1)
                # от первой до предпоследней точки извлекаем эту точку и следующую, так как i начинается с 0, берем i+1 и i+2
                if i < len(inter_point) - 1:
                    
                    query_inter_poin = '"OBJECTID" = {0} OR "OBJECTID" = {1}'.format((i+1),(i+2))
                    arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "i_point", query_inter_poin)
                    # режем линию по этим двум точкам (1 линия - сверху, посередине, последняя линия - снизу, нам нужна та, что в серединке)
                    arcpy.management.SplitLineAtPoint(aval_tranz_zone_flip, 'i_point', "i_stream", "1 Meters")
                    with arcpy.da.SearchCursor(aval_tranz_zone_flip, 'SHAPE@') as cursor:
                        for row in cursor:
                            coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                            break
                    objval_2 = 0
                    with arcpy.da.SearchCursor('i_stream', ['SHAPE@', 'OID@']) as cursor:
                        for row in cursor:
                            split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                            split_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                            if (coords_start != split_start and coords_end != split_end):
                                objval_2 = row[1]
                                break
                    query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
                # если точка последняя, то режем по ней и берем первую линию
                else:
                    query_inter_poin = '"OBJECTID" = {0}'.format(i+1)
                    arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "i_point", query_inter_poin)
                    arcpy.management.SplitLineAtPoint(aval_tranz_zone_flip, 'i_point', "i_stream", "1 Meters")
                    with arcpy.da.SearchCursor(aval_tranz_zone_flip, 'SHAPE@') as cursor:
                        for row in cursor:
                            coords_start = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                            break
                    objval_2 = 0
                    with arcpy.da.SearchCursor('i_stream', ['SHAPE@', 'OID@']) as cursor:
                        for row in cursor:
                            split_start = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                            if (coords_start == split_start):
                                objval_2 = row[1]
                                break
                    query_line_2 = '"OBJECTID" = {0}'.format(objval_2)

                
                arcpy.MakeFeatureLayer_management('i_stream', "i_stream_interest", query_line_2)
                # результатом является линия между двумя точками или последняя линия
                # к ней добавляем длину в метрах и извлекаем ее
                arcpy.management.AddGeometryAttributes('i_stream_interest', "LENGTH","METERS")
                len_i_line = [k[0] for k in arcpy.da.SearchCursor('i_stream_interest', "LENGTH")][0]
                # если длина выбранной линии больше порога, то заходим в цикл
                if len_i_line >= len_treshold_line:
                    query_inter_poin_interest = '"OBJECTID" = {0}'.format(i+1)
                    # добавляем начальную точку в общий список под уникальным именем
                    arcpy.MakeFeatureLayer_management('intersect_point_25_sing', point_i, query_inter_poin_interest)
                    point_list.append(point_i)
            

                # создаем единый массив точек
            arcpy.Merge_management(point_list, "point_intersect_len")

           
            # смотрим на длину массива
            count_line_i = [k[0] for k in arcpy.da.SearchCursor('point_intersect_len', "OBJECTID")]
            query_point_25 = '"OBJECTID" = {0}'.format(count_line_i[-1])
            # находим точку перегиба 
            arcpy.MakeFeatureLayer_management('point_intersect_len', "point_25_degree_end", query_point_25)

        # дальше смотрим на то, нет ли пересечений сверху и если есть, то выделяем его
        # находим верхнюю точку НЕ перевернутой линии
            arcpy.FeatureVerticesToPoints_management('aval_tranz_zone', "start_end_point", "BOTH_ENDS")
            arcpy.sa.ExtractValuesToPoints('start_end_point', DEM_fill, "start_end_point_xyz")
            s_e_points = [i[0] for i in arcpy.da.SearchCursor('start_end_point_xyz', "RASTERVALU")]
            razn_z_start_end = s_e_points[0]-s_e_points[1]
            if razn_z_start_end > 0:
                query_point_start_end = '"OBJECTID" = 1'
            else:
                query_point_start_end = '"OBJECTID" = 2'
            arcpy.MakeFeatureLayer_management('start_end_point_xyz', "start_point", query_point_start_end)
            list_2_3 = ['start_point', 'point_25_degree_end']
            arcpy.Merge_management(list_2_3, "start_25")
            arcpy.MakeFeatureLayer_management('start_25', "start_25_fl")
            # смотрим есть ли пересечение этой точки и водотока (выделение инвертируем)
            arcpy.management.SelectLayerByLocation('start_25_fl' , "INTERSECT", watershed_output , "","NEW_SELECTION")
            # если пересечений нет, то значит точка лежит выше полигона водораздела и мы должны найти точку пересечения
            arcpy.MakeFeatureLayer_management('start_25_fl', "start_point_inter")
            len_inter_0 = len([i[0] for i in arcpy.da.SearchCursor('start_point_inter', "OBJECTID")])

            if len_inter_0 == 1:
                # в случае, если точка лежит выше водораздела, то точкой пересечения с линией в 25 градусов считаем верхнюю из точек пересечения
                start_point_25 = [i[0] for i in arcpy.da.SearchCursor('intersect_point_25_sing', "OBJECTID")][0]
                query_start_point_25 = '"OBJECTID" = {0}'.format(start_point_25)
                arcpy.MakeFeatureLayer_management('intersect_point_25_sing', "point_25_degree_start", query_start_point_25) #point_25_degree_start
                arcpy.management.SplitLineAtPoint('dissolve_stream', 'point_25_degree_start', "line_25_degree", "1 Meters")
                
                with arcpy.da.SearchCursor('dissolve_stream', 'SHAPE@') as cur:
                    for row in cur:
                        coords_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        break
                objval_2 = 0
                with arcpy.da.SearchCursor('line_25_degree', ['SHAPE@', 'OID@']) as cur_1:
                    for row in cur_1:
                        split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        if (coords_start != split_start):
                            objval_2 = row[1]
                            break
                query_line_25_before = '"OBJECTID" = {0}'.format(objval_2)
                arcpy.MakeFeatureLayer_management('line_25_degree', "line_to_wsh", query_line_25_before)



                



            else:

                arcpy.management.AddGeometryAttributes('start_point', "POINT_X_Y_Z_M","METERS")
                arcpy.management.PolygonToLine(watershed_output, "watershed_output_line")
                arcpy.MakeFeatureLayer_management('watershed_output_line', "watershed_output_line_fl")
                arcpy.management.FeatureVerticesToPoints('watershed_output_line_fl', "point_watershed_output_line_fl", "ALL")
                arcpy.management.AddGeometryAttributes('point_watershed_output_line_fl', "POINT_X_Y_Z_M","METERS")
                px_sz = [k[0] for k in arcpy.da.SearchCursor('point_watershed_output_line_fl', "POINT_X")]
                py_sz = [k[0] for k in arcpy.da.SearchCursor('point_watershed_output_line_fl', "POINT_Y")]
                arcpy.management.AddGeometryAttributes('start_point', "POINT_X_Y_Z_M","METERS")
                px_25_start = [k[0] for k in arcpy.da.SearchCursor('start_point', "POINT_X")][0]
                py_20_start = [k[0] for k in arcpy.da.SearchCursor('start_point', "POINT_Y")][0]
                ro_20_sz_list = []
                for i in range(len(px_sz)):
                    razn_x_sz_20 = abs(px_25_start - px_sz[i]) 
                    razn_y_sz_20 = abs(py_20_start - py_sz[i])
                    ro_20_sz = math.sqrt(razn_x_sz_20**2 + razn_y_sz_20**2)
                    ro_20_sz_list.append(ro_20_sz)
                id_point_watershed = ro_20_sz_list.index(min(ro_20_sz_list))
                query_point_watershed = '"OBJECTID" = {0}'.format(id_point_watershed)
                arcpy.MakeFeatureLayer_management('point_watershed_output_line_fl', "point_wsh_min_dist", query_point_watershed)
                point_start_wsh_list = ['point_wsh_min_dist', 'start_point']
                arcpy.Merge_management(point_start_wsh_list, "point_start_wsh")
                arcpy.management.PointsToLine('point_start_wsh', 'point_start_wsh_line')
                merge_watershed_zone_line = ['point_start_wsh_line', 'dissolve_stream']
                arcpy.Merge_management(merge_watershed_zone_line, "line_to_wsh_2")
                arcpy.Dissolve_management('line_to_wsh_2', "line_to_wsh","", "", "SINGLE_PART", "DISSOLVE_LINES")


        arcpy.AddMessage('5. Point end tranzit zone ok')



# ПОИСК ПОЛИГОНА 3ОНЫ ТРАН3ИТА
        remap_20 = arcpy.sa.RemapRange([[0,2000,0],[2000,6000,1],[6000,9000,0]])
        slope_reclass_20 = arcpy.sa.Reclassify(Slope_fill, "Value", remap_20, "NODATA")
        # 3.1.4. превращение растра в полигоны и отбор (оставляются только полигоны с углами наклона более25 градусов)
        arcpy.conversion.RasterToPolygon(slope_reclass_20, "slope_polygon_20", "NO_SIMPLIFY", "Value")
        query_slope_20 = '"gridcode" = 1'
        # 3.1.5.превращение полигонов в линии
        arcpy.MakeFeatureLayer_management('slope_polygon_20', "slope_poly_20", query_slope_20)
        arcpy.management.PolygonToLine('slope_poly_20', "slope_line_20")
        arcpy.management.AddGeometryAttributes('slope_line_20', "LENGTH","METERS")
        arcpy.management.Sort('slope_line_20', "slope_line_20_sort", [["LENGTH", "DESCENDING"]])
        len_slope_max = [i[0] for i in arcpy.da.SearchCursor('slope_line_20_sort', "LENGTH")][0]
        len_threshold = len_slope_max * 10 / 100
        query_len = '"LENGTH" > {0}'.format(len_threshold)
        arcpy.MakeFeatureLayer_management('slope_line_20', "slope_line_20_len", query_len)
        arcpy.Dissolve_management('slope_line_20_len', "slope_line_dis_20", "", "", "MULTI_PART", "UNSPLIT_LINES")
        arcpy.analysis.Intersect(["slope_line_dis_20", 'aval_tranz_zone'] , "inter_slope_20_to_split", "", "", "POINT")
        arcpy.management.SplitLineAtPoint('aval_tranz_zone', 'inter_slope_20_to_split', "stream_20_line_split", "1 Meters")
        arcpy.management.AddGeometryAttributes('stream_20_line_split', "LENGTH","METERS")
        arcpy.management.Sort('stream_20_line_split', "stream_20_line_split_sort", [["LENGTH", "DESCENDING"]])
        query_most_len_line_20 = '"OBJECTID" = 1'
        arcpy.MakeFeatureLayer_management('stream_20_line_split_sort',  "most_len_line_20", query_most_len_line_20)
        # 3.2.1. создание растра водораздела и конвертация его в вектор
        out_watershed_raster_20 = arcpy.sa.Watershed(flow_directions, 'point_zone_20')
        arcpy.conversion.RasterToPolygon(out_watershed_raster_20, "out_watershed_polygon_20", "NO_SIMPLIFY", "Value")
        arcpy.MakeFeatureLayer_management('out_watershed_polygon_20', "watershed_poly_20")
        arcpy.management.PolygonToLine('watershed_poly_20', "watershed_line_20")
        # 3.2.3. разрезание изогоны 25 градусов и линий водоразделов по точкам пересечения
        arcpy.FeatureVerticesToPoints_management('watershed_line_20', "watershed_vertex_20", "ALL")
        arcpy.management.SplitLineAtPoint('watershed_line_20', 'watershed_vertex_20', "watershed_line_split_vertex_20", "1 Meters")
        arcpy.FeatureVerticesToPoints_management('slope_line_dis_20', "slope_layer_inter_vertex_20", "ALL")
        arcpy.management.SplitLineAtPoint('slope_line_dis_20', 'slope_layer_inter_vertex_20', "slope_layer_split_vertex_20", "1 Meters")
        arcpy.analysis.Intersect(['slope_layer_split_vertex_20', 'watershed_line_split_vertex_20'], "point_output_split_poly_20", "", "", "POINT")
        arcpy.management.SplitLineAtPoint('slope_layer_split_vertex_20', 'point_output_split_poly_20', "slope_layer_inter_split_20", "1 Meters")
        arcpy.management.SplitLineAtPoint('watershed_line_split_vertex_20', 'point_output_split_poly_20', "watershed_line_split_20", "1 Meters")
        # 3.2.4. сохранение двух линий на один слой
        merge_list_watershed_20 = ["slope_layer_inter_split_20", "watershed_line_split_20"]
        arcpy.Merge_management(merge_list_watershed_20, "watershed_line_20")
        # 3.2.5. создание полигонов из линий
        arcpy.management.FeatureToPolygon('watershed_line_20', "water_polygon_all_20")
        # 3.2.5. поиск и сохранение полигона, пересекающего тальвег
        arcpy.MakeFeatureLayer_management('water_polygon_all_20',  "water_polygon_all_fl_20")
        arcpy.management.SelectLayerByLocation('water_polygon_all_fl_20', "INTERSECT", 'most_len_line_20')
        arcpy.MakeFeatureLayer_management('water_polygon_all_fl_20', "watershed_intersect_20")
        arcpy.management.AddGeometryAttributes('watershed_intersect_20', "AREA", "", "SQUARE_METERS")
        arcpy.management.Sort('watershed_intersect_20', "watershed_intersect_sort_20", [["POLY_AREA", "DESCENDING"]])
        query_area_poly_20 = '"OBJECTID" = 1'
        arcpy.MakeFeatureLayer_management('watershed_intersect_sort_20', "area_poly_20", query_area_poly_20)
        arcpy.analysis.SymDiff('area_poly_20', watershed_output, "zone_polygon_all")
        arcpy.analysis.Intersect(['zone_polygon_all', 'aval_tranz_zone'], "point_int_zone_polygon_multi", "", "", "POINT")
        arcpy.management.MultipartToSinglepart('point_int_zone_polygon_multi', "point_int_zone_polygon_single")
        arcpy.sa.ExtractValuesToPoints('point_int_zone_polygon_single', DEM_fill, "point_int_zone_polygon_all_height")
        arcpy.management.Sort('point_int_zone_polygon_all_height', "point_int_zone_polygon_all_height_sort", [["RASTERVALU", "ASCENDING"]])
        point_2_down = [i[0] for i in arcpy.da.SearchCursor('point_int_zone_polygon_all_height_sort', "OBJECTID")][0]
        query_area_poly_20 = '"OBJECTID" =  {0}'.format(point_2_down)
        arcpy.MakeFeatureLayer_management('point_int_zone_polygon_all_height_sort', "point_int_20_down", query_area_poly_20)
        arcpy.MakeFeatureLayer_management('zone_polygon_all', "zone_polygon_all_fl")
        arcpy.management.MultipartToSinglepart('zone_polygon_all_fl', "zone_polygon_all_fl_single")
        arcpy.MakeFeatureLayer_management('zone_polygon_all_fl_single', "zone_polygon_all_fl_single_fl")
        arcpy.management.SelectLayerByLocation('zone_polygon_all_fl_single_fl', "INTERSECT", 'point_int_20_down')
        arcpy.MakeFeatureLayer_management('zone_polygon_all_fl_single_fl', "tranzit_zone_polygon_no_20")
        arcpy.management.PolygonToLine('tranzit_zone_polygon_no_20', "tranzit_zone_no_20_line")
        arcpy.MakeFeatureLayer_management('tranzit_zone_no_20_line', "tranzit_zone_no_20_line_fl")
        arcpy.management.FeatureVerticesToPoints('tranzit_zone_no_20_line_fl', "point_tranzit_zone_no_20", "ALL")
        arcpy.management.AddGeometryAttributes('point_tranzit_zone_no_20', "POINT_X_Y_Z_M","METERS")
        px_tz = [k[0] for k in arcpy.da.SearchCursor('point_tranzit_zone_no_20', "POINT_X")]
        py_tz = [k[0] for k in arcpy.da.SearchCursor('point_tranzit_zone_no_20', "POINT_Y")]
        arcpy.management.AddGeometryAttributes('20_degree', "POINT_X_Y_Z_M","METERS")
        px_20 = [k[0] for k in arcpy.da.SearchCursor('20_degree', "POINT_X")][0]
        py_20 = [k[0] for k in arcpy.da.SearchCursor('20_degree', "POINT_Y")][0]
        ro_20_zt_list = []
        for i in range(len(px_tz)):
            razn_x_zt_20 = abs(px_20 - px_tz[i]) 
            razn_y_zt_20 = abs(py_20 - py_tz[i])
            ro_20_zt = math.sqrt(razn_x_zt_20**2 + razn_y_zt_20**2)
            ro_20_zt_list.append(ro_20_zt)
        min_dist_20_tz = math.ceil(min(ro_20_zt_list) + cell_p/2)
        arcpy.edit.Snap('tranzit_zone_no_20_line', [['20_degree', "VERTEX",  min_dist_20_tz]])
        arcpy.management.FeatureToPolygon('tranzit_zone_no_20_line', "tranzit_zone_polygon_20")
        arcpy.management.SelectLayerByLocation('zone_polygon_all_fl_single_fl', "INTERSECT", 'point_25_degree_end')
        arcpy.MakeFeatureLayer_management('zone_polygon_all_fl_single_fl', "tranzit_zone_polygon_no_20_2")
        tranzit_zone_list =['tranzit_zone_polygon_20', 'tranzit_zone_polygon_no_20_2']
        arcpy.Merge_management(tranzit_zone_list, "tranzit_zone_list_2")
        arcpy.MakeFeatureLayer_management('tranzit_zone_list_2', "tranzit_zone_polygon_fl")
        arcpy.Dissolve_management('tranzit_zone_list_2', "tranz_diss")
        tranzit_zone_polygon = arcpy.MakeFeatureLayer_management('tranz_diss', tranzit_zone_polygon)
        arcpy.AddMessage('6. Tranzit zone polygon ok')





# ВЫДЕЛЕНИЕ ОТДЕЛЬНЫХ ЛИНИЙ
        arcpy.MakeFeatureLayer_management('point_25_degree_end', "25_degree")
        arcpy.Merge_management(point_list_interest_point, "point_20_25_30") 
        arcpy.management.SplitLineAtPoint('line_to_wsh', 'point_20_25_30', "avalanche_path_component", "1 Meters") 
        query_start = '"OBJECTID" = 1'
        start_track = arcpy.MakeFeatureLayer_management('avalanche_path_component', start_track, query_start)
        with arcpy.da.SearchCursor(start_track, 'SHAPE@') as cur:
            for row in cur:
                coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                break
        objval_2 = 0
        with arcpy.da.SearchCursor('avalanche_path_component', ['SHAPE@', 'OID@']) as cur_1:
            for row in cur_1:
                split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                if (coords_end == split_start):
                    objval_2 = row[1]
                    break
        query_tranzit = '"OBJECTID" = {0}'.format(objval_2)
        tranzit_track = arcpy.MakeFeatureLayer_management('avalanche_path_component', tranzit_track, query_tranzit)
        with arcpy.da.SearchCursor(tranzit_track, 'SHAPE@') as cur:
            for row in cur:
                coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                break
        objval_2 = 0
        with arcpy.da.SearchCursor('avalanche_path_component', ['SHAPE@', 'OID@']) as cur_1:
            for row in cur_1:
                split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                if (coords_end == split_start):
                    objval_2 = row[1]
                    break
        query_runout = '"OBJECTID" = {0}'.format(objval_2)
        arcpy.MakeFeatureLayer_management('avalanche_path_component', "runout_zone_before_30", query_runout)
        len_path_comp_count = len([i[0] for i in arcpy.da.SearchCursor('avalanche_path_component', "OBJECTID")])
        arcpy.AddMessage('7. Line start and tranzit zone ok')


 
# ПРОДЛЯЕМ ЛИНИЮ 3ОНЫ ВЫХОДА, ЕСЛИ ОНА БОЛЬШЕ ТРИДЦАТИ ГРАДУСОВ
        if len_path_comp_count == 4:
            arcpy.FeatureVerticesToPoints_management(start_track, "start_end_point_tranzit", "BOTH_ENDS")
            arcpy.management.AddGeometryAttributes('start_end_point_tranzit', "POINT_X_Y_Z_M","METERS")
            arcpy.FeatureVerticesToPoints_management('runout_zone_before_30', "start_end_point_runout", "BOTH_ENDS")
            arcpy.management.AddGeometryAttributes('start_end_point_runout', "POINT_X_Y_Z_M","METERS")
            px_t = [k[0] for k in arcpy.da.SearchCursor('start_end_point_tranzit', "POINT_X")]
            py_t = [k[0] for k in arcpy.da.SearchCursor('start_end_point_tranzit', "POINT_Y")]
            px_r = [k[0] for k in arcpy.da.SearchCursor('start_end_point_runout', "POINT_X")][0]
            py_r = [k[0] for k in arcpy.da.SearchCursor('start_end_point_runout', "POINT_Y")][0]
            razn_tranzit_x = px_t[0] - px_t[1]
            razn_tranzit_y = py_t[0] - py_t[1]
            ro_x_t = abs(razn_tranzit_x)
            ro_y_t = abs(razn_tranzit_y)

            if razn_tranzit_x == 0:
                angle_t = 0
            if razn_tranzit_y == 0:
                angle_t = 90
            if razn_tranzit_x > 0 and razn_tranzit_y > 0:
                tan_a = ro_x_t/ro_y_t
                angle_t = math.degrees(math.atan(tan_a)) + 180
            if razn_tranzit_x > 0 and razn_tranzit_y < 0:
                tan_a = ro_x_t/ro_y_t
                angle_t = 360 - math.degrees(math.atan(tan_a))
            if razn_tranzit_x < 0 and razn_tranzit_y > 0:
                tan_a = ro_x_t/ro_y_t
                angle_t = 180 - math.degrees(math.atan(tan_a))
            if razn_tranzit_x < 0 and razn_tranzit_y < 0:
                tan_a = ro_x_t/ro_y_t
                angle_t = math.degrees(math.atan(tan_a))

            if angle_t > 0 and angle_t <= 90:
                angle_len = 90 - angle_t
                d_x = (len_runout_after_30_degree + 100) *  math.cos(math.radians(angle_len))
                d_y = (len_runout_after_30_degree + 100) * math.sin(math.radians(angle_len))
                x_new = px_r + d_x
                y_new = py_r + d_y
            if angle_t > 90 and angle_t <= 180:
                angle_len = angle_t - 90
                d_x = (len_runout_after_30_degree + 100) *  math.cos(math.radians(angle_len))
                d_y = (len_runout_after_30_degree + 100) * math.sin(math.radians(angle_len))
                x_new = px_r + d_x
                y_new = py_r - d_y
            if angle_t > 180 and angle_t <= 270:
                angle_len = 270 - angle_t
                d_x = (len_runout_after_30_degree + 100) *  math.cos(math.radians(angle_len))
                d_y = (len_runout_after_30_degree + 100) * math.sin(math.radians(angle_len))
                x_new = px_r - d_x
                y_new = py_r - d_y
            if angle_t > 270 and angle_t <= 360:
                angle_len = angle_t - 270
                d_x = (len_runout_after_30_degree + 100) *  math.cos(math.radians(angle_len))
                d_y = (len_runout_after_30_degree + 100) * math.sin(math.radians(angle_len))
                x_new = px_r - d_x
                y_new = py_r + d_y
            if angle_t == 0 and razn_tranzit_y > 0:
                d_x = (len_runout_after_30_degree + 100) *  math.cos(math.radians(angle_len))
                d_y = (len_runout_after_30_degree + 100) * math.sin(math.radians(angle_len))
                x_new = px_r
                y_new = py_r - d_y
            if angle_t == 0 and razn_tranzit_y < 0:
                d_x = (len_runout_after_30_degree + 100) *  math.cos(math.radians(angle_len))
                d_y = (len_runout_after_30_degree + 100) * math.sin(math.radians(angle_len))
                x_new = px_r
                y_new = py_r + d_y
            if angle_t == 90 and razn_tranzit_x > 0:
                d_x = (len_runout_after_30_degree + 100) *  math.cos(math.radians(angle_len))
                d_y = (len_runout_after_30_degree + 100) * math.sin(math.radians(angle_len))
                x_new = px_r - d_x
                y_new = py_r 
            if angle_t == 90 and razn_tranzit_x < 0:
                d_x = (len_runout_after_30_degree + 100) *  math.cos(math.radians(angle_len))
                d_y = (len_runout_after_30_degree + 100) * math.sin(math.radians(angle_len))
                x_new = px_r + d_x
                y_new = py_r 

            sr = arcpy.SpatialReference()
            coord_syst_wkt = '%s' % coord_syst
            sr.loadFromString(coord_syst_wkt)
            pt = arcpy.Point(x_new, y_new)
            pt_geometry = arcpy.PointGeometry(pt, sr)
            point_ptr = arcpy.management.CreateFeatureclass("in_memory", "point_ptr", "POINT", "", "DISABLED", "DISABLED", spatial_reference=sr)
            with arcpy.da.InsertCursor(point_ptr, ["SHAPE@"]) as cursor:
                cursor.insertRow([pt_geometry])
            arcpy.MakeFeatureLayer_management(point_ptr, "point_30_end")
            point_runout_zone = ['30_degree', 'point_30_end']
            arcpy.Merge_management(point_runout_zone, "point_runout_zone_st_end")
            arcpy.management.PointsToLine('point_runout_zone_st_end', "runout_zone_line_after_30")
            merge_runout_zone_line = ['runout_zone_before_30', 'runout_zone_line_after_30']
            arcpy.Merge_management(merge_runout_zone_line, "runout_zone_line_with_30")
            arcpy.Dissolve_management('runout_zone_line_with_30', "runout_zone_line","", "", "SINGLE_PART", "DISSOLVE_LINES")
            arcpy.MakeFeatureLayer_management('runout_zone_line', "runout_track_no_end")
            arcpy.AddMessage('8. Runout line ok')
        else:
            arcpy.FeatureVerticesToPoints_management(start_track, "start_end_point_tranzit", "BOTH_ENDS")
            arcpy.management.AddGeometryAttributes('start_end_point_tranzit', "POINT_X_Y_Z_M","METERS")
            px_t = [k[0] for k in arcpy.da.SearchCursor('start_end_point_tranzit', "POINT_X")]
            py_t = [k[0] for k in arcpy.da.SearchCursor('start_end_point_tranzit', "POINT_Y")]
            arcpy.MakeFeatureLayer_management('runout_zone_before_30', "runout_track_no_end")
            arcpy.AddMessage('8. Runout line ok_2')


# ПОИСК СРЕДНЕГО УГЛА НАКЛОНА
        arcpy.edit.Densify(start_track, "DISTANCE", cell_p)
        arcpy.FeatureVerticesToPoints_management(start_track, "start_track_point", "ALL")
        arcpy.sa.ExtractValuesToPoints('start_track_point', slope_degree, "start_track_point_slope")
        slope_start_zone = [k[0] for k in arcpy.da.SearchCursor('start_track_point_slope', "RASTERVALU")]
        sum = 0
        for i in range(len(slope_start_zone)):
            sum += slope_start_zone[i]
        median_slope = sum/len(slope_start_zone)
        arcpy.AddMessage('9. Median slope ok')


# ПОИСК ПЛОЩАДИ 3ОНЫ 3АРОЖДЕНИЯ
        area_start_zone = [k[0] for k in arcpy.da.SearchCursor(watershed_output, "POLY_AREA")][0]
        arcpy.AddMessage('10. Start zone area ok')


# ПОИСК ТАНГЕНСА УГЛА НАКЛОНА
        log_snow = math.log(float(snow_height))
        area_ga = -0.0001 * area_start_zone
        e_st = math.e ** (area_ga * (1/(43.33688899958995 - 4.101023511027784 *log_snow)))
        tan_psi_threshold = (0.082 - 0.034 * log_snow ) + (0.013 + 0.019 * log_snow) * e_st + (0.022 - 0.001 * log_snow) * median_slope

        arcpy.AddMessage('11. Tan threshold ok')


# ПОИСК ТОЧКИ ОКОНЧАНИЯ
        arcpy.management.AddGeometryAttributes(start_track, "LENGTH","METERS")
        len_start = [k[0] for k in arcpy.da.SearchCursor(start_track, "LENGTH")][0]
        arcpy.management.AddGeometryAttributes(tranzit_track, "LENGTH","METERS")
        len_tranzit = [k[0] for k in arcpy.da.SearchCursor(tranzit_track, "LENGTH")][0]
        arcpy.FeatureVerticesToPoints_management(start_track, "start_track_poin_aval", "BOTH_ENDS")
        arcpy.sa.ExtractValuesToPoints('start_track_poin_aval', DEM_fill, "start_track_poin_aval_val")
        s_e_points_start_zone = [i[0] for i in arcpy.da.SearchCursor('start_track_poin_aval_val', "RASTERVALU")]
        razn_z_start_end_aval = s_e_points_start_zone[0]-s_e_points_start_zone[1]
        if razn_z_start_end_aval > 0:
            z_start_point = s_e_points_start_zone[0]
        else:
            z_start_point = s_e_points_start_zone[1]

        arcpy.edit.Densify('runout_track_no_end', "DISTANCE", cell_p)
        arcpy.FeatureVerticesToPoints_management('runout_track_no_end', "runout_track_point", "ALL")
        arcpy.sa.ExtractValuesToPoints('runout_track_point', DEM_fill, "runout_track_point_value")
        value_z_runout = [i[0] for i in arcpy.da.SearchCursor('runout_track_point_value', "RASTERVALU")]
        angle_psi = []
        cnt = 0
        for i in range(len(value_z_runout) - 1):
            if cnt >= 2:
                selection_query_1 = '"OBJECTID" = {0}'.format(i)
                arcpy.MakeFeatureLayer_management('runout_track_point_value', "current_points_runout", selection_query_1)
                arcpy.management.SplitLineAtPoint('runout_track_no_end', 'current_points_runout', "splitted_fclass_runout", "1 Meters")
                with arcpy.da.SearchCursor(tranzit_track, 'SHAPE@') as cur:
                    for row in cur:
                        coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                        break
                objval_2 = 0
                with arcpy.da.SearchCursor('splitted_fclass_runout', ['SHAPE@', 'OID@']) as cur_1:
                    for row in cur_1:
                        split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                        if (coords_end == split_start):
                            objval_2 = row[1]
                            break
                query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
                arcpy.MakeFeatureLayer_management('splitted_fclass_runout', "i_stream_runout")
                arcpy.management.AddGeometryAttributes('i_stream_runout', "LENGTH","METERS")
                len_runout = [k[0] for k in arcpy.da.SearchCursor('i_stream_runout', "LENGTH")][0]
                len_path = len_runout + len_tranzit + len_start
                razn_z_start_end_aval = z_start_point - value_z_runout[i]
                tan_psi_i = razn_z_start_end_aval/len_path
                angle_psi.append(tan_psi_i)
            cnt += 1
        point_qery_list = [angle_psi.index(i) for i in angle_psi]
        point_end_aval = [angle_psi.index(i) for i in angle_psi if i <= tan_psi_threshold][1]
        point_end_aval_query = '"OBJECTID" = {0}'.format(point_end_aval)
        arcpy.MakeFeatureLayer_management('runout_track_point_value', "point_avalance_end_1", point_end_aval_query)
        arcpy.management.AddGeometryAttributes('point_avalance_end_1', "POINT_X_Y_Z_M","METERS")
        px_roe = [k[0] for k in arcpy.da.SearchCursor('point_avalance_end_1', "POINT_X")][0]
        py_roe = [k[0] for k in arcpy.da.SearchCursor('point_avalance_end_1', "POINT_Y")][0]
        arcpy.AddMessage(px_roe)
        arcpy.AddMessage(py_roe)

        arcpy.FeatureVerticesToPoints_management(tranzit_track, "tranzit_track_end_point", "BOTH_ENDS")
        arcpy.management.AddGeometryAttributes('tranzit_track_end_point', "POINT_X_Y_Z_M","METERS")
        px_tre = [k[0] for k in arcpy.da.SearchCursor('tranzit_track_end_point', "POINT_X")][-1]
        py_tre = [k[0] for k in arcpy.da.SearchCursor('tranzit_track_end_point', "POINT_Y")][-1]

        if px_roe == px_tre and py_roe == py_tre:
            point_end_aval_query_1 = '"OBJECTID" = {0}'.format(point_qery_list[2])
            arcpy.MakeFeatureLayer_management('runout_track_point_value', "point_avalance_end", point_end_aval_query_1)
        else:
            point_end_aval_query = '"OBJECTID" = {0}'.format(point_end_aval)
            arcpy.MakeFeatureLayer_management('runout_track_point_value', "point_avalance_end", point_end_aval_query)

        arcpy.AddMessage('12. Point avalance end ok')



# ПОИСК ЛИНИИ ЗОНЫ ОСАЖДЕНИЯ
        arcpy.management.SplitLineAtPoint('runout_track_no_end', 'point_avalance_end', "runout_track_no_end_i", "1 Meters")
        with arcpy.da.SearchCursor(tranzit_track, 'SHAPE@') as cur:
            for row in cur:
                coords_end = tuple((row[0].lastPoint.X, row[0].lastPoint.Y))
                break
        objval_2 = 0
        with arcpy.da.SearchCursor('runout_track_no_end_i', ['SHAPE@', 'OID@']) as cur_1:
            for row in cur_1:
                split_start = tuple((row[0].firstPoint.X, row[0].firstPoint.Y))
                if (coords_end == split_start):
                    objval_2 = row[1]
                    break
        query_line_2 = '"OBJECTID" = {0}'.format(objval_2)
        runout_track = arcpy.MakeFeatureLayer_management('runout_track_no_end_i', runout_track, query_line_2)
        arcpy.AddMessage('13. Runout line ok')




# ПОИСК ПОЛИГОНА ЗОНЫ ОСАЖДЕНИЯ
        arcpy.analysis.Intersect([watershed_output, 'tranzit_zone_polygon_fl'] , "inter_wsh_and_tranz", "", "", "LINE")
        inter_line_count = len([k[0] for k in arcpy.da.SearchCursor('inter_wsh_and_tranz', "OBJECTID")])
        if inter_line_count == 1:
            arcpy.MakeFeatureLayer_management('inter_wsh_and_tranz','inter_wsh_and_tranz_fl')
        else:
            arcpy.Dissolve_management('inter_wsh_and_tranz', "inter_wsh_and_tranz_fl", "", "", "SINGLE_PART", "DISSOLVE_LINES")
        arcpy.FeatureVerticesToPoints_management('inter_wsh_and_tranz_fl', "intersect_point_w_t", "BOTH_ENDS") 
        query_start_inter = '"OBJECTID" = 1'
        query_end_inter = '"OBJECTID" = 2'
        arcpy.MakeFeatureLayer_management('intersect_point_w_t',"intersect_point_w_t_1", query_start_inter)
        arcpy.MakeFeatureLayer_management('intersect_point_w_t',"intersect_point_w_t_2", query_end_inter)

        runout_list_1 = ['point_avalance_end', 'intersect_point_w_t_1']
        arcpy.Merge_management(runout_list_1, "runout_point_s")
        runout_list_2 = ['point_avalance_end', 'intersect_point_w_t_2']
        arcpy.Merge_management(runout_list_2, "runout_point_e")

        arcpy.MakeFeatureLayer_management('runout_point_s',"runout_point_s_fl")
        arcpy.MakeFeatureLayer_management('runout_point_e',"runout_point_e_fl")

        arcpy.management.PointsToLine('runout_point_s_fl', "runout_point_s_fl_line")
        arcpy.management.PointsToLine('runout_point_e_fl', "runout_point_e_fl_line")

        line_list_runout = ['inter_wsh_and_tranz_fl', 'runout_point_s_fl_line', 'runout_point_e_fl_line']
        arcpy.Merge_management(line_list_runout, "runout_line")
        arcpy.management.FeatureToPolygon('runout_line', "runout_zone_polygon")

        arcpy.analysis.SymDiff('runout_zone_polygon', 'tranzit_zone_list_2', "runout_polygon_all")
        arcpy.management.MultipartToSinglepart('runout_polygon_all', "runout_polygon_all_sing")
        arcpy.MakeFeatureLayer_management('runout_polygon_all_sing',"runout_polygon_all_sing_fl")
        arcpy.management.SelectLayerByLocation('runout_polygon_all_sing_fl', "INTERSECT", 'point_avalance_end')
        runout_polygon = arcpy.MakeFeatureLayer_management('runout_polygon_all_sing_fl',runout_polygon)
        arcpy.AddMessage('14. Runout area ok')



#ПОИСК ЗНАЧЕНИЯ СКОРОСТИ ЛАВИНЫ ДЛЯ ТОЧКИ В КОНЦЕ ЗОНЫ ЗАРОЖДЕНИЯ
        arcpy.sa.ExtractValuesToPoints('25_degree', DEM_fill, "dem_25_degree_value")
        z_25_point = [k[0] for k in arcpy.da.SearchCursor('dem_25_degree_value', "RASTERVALU")][0]
        Hb_25 = z_start_point - z_25_point
        z_end_point = [k[0] for k in arcpy.da.SearchCursor('point_avalance_end', "RASTERVALU")][0]
        H = z_start_point - z_end_point
        arcpy.management.AddGeometryAttributes(runout_track, "LENGTH","METERS")
        len_runout = [k[0] for k in arcpy.da.SearchCursor(runout_track, "LENGTH")][0]
        L = len_runout + len_tranzit + len_start
        lb_25 = len_start
        Z_25 = Hb_25 - (H/L)*lb_25
        if Z_25 < 0:
            z_25 = 0
        else:
            z_25 = Z_25
        v_25 = math.sqrt(2*9.8*z_25)


#ПОИСК ЗНАЧЕНИЯ СКОРОСТИ ЛАВИНЫ ДЛЯ ТОЧКИ В КОНЦЕ ЗОНЫ ТРАНЗИТА
        z_20_point = [k[0] for k in arcpy.da.SearchCursor('20_degree', "RASTERVALU")][0]
        Hb_20 = z_start_point - z_20_point
        lb_20 = len_start + len_tranzit
        Z_20 = Hb_20 - (H/L)*lb_20
        if Z_20 < 0:
            z_20 = 0
        else:
            z_20 = Z_20
        v_20 = math.sqrt(2*9.8*z_20)


# ПОДГОТОВКА ДАННЫХ ДЛЯ ЗАПИСИ В ТЕКСТОРВЫЙ ФАЙЛ
        coords_start_x = px_t[0]
        coords_start_y = py_t[0]

        arcpy.management.AddGeometryAttributes('25_degree', "POINT_X_Y_Z_M","METERS")
        coords_25_x = [k[0] for k in arcpy.da.SearchCursor('25_degree', "POINT_X")][0]
        coords_25_y = [k[0] for k in arcpy.da.SearchCursor('25_degree', "POINT_Y")][0]

        arcpy.management.AddGeometryAttributes('20_degree', "POINT_X_Y_Z_M","METERS")
        coords_25_x = [k[0] for k in arcpy.da.SearchCursor('25_degree', "POINT_X")][0]
        coords_25_y = [k[0] for k in arcpy.da.SearchCursor('25_degree', "POINT_Y")][0]

        coords_20_x = px_20
        coords_20_y = py_20

        arcpy.management.AddGeometryAttributes('point_avalance_end', "POINT_X_Y_Z_M","METERS")
        coords_end_x = [k[0] for k in arcpy.da.SearchCursor('point_avalance_end', "POINT_X")][0]
        coords_end_y = [k[0] for k in arcpy.da.SearchCursor('point_avalance_end', "POINT_Y")][0]

        arcpy.management.AddGeometryAttributes(watershed_output, "AREA", "", "SQUARE_METERS")
        area_start_zone = [k[0] for k in arcpy.da.SearchCursor(watershed_output, "POLY_AREA")][0]

        arcpy.management.AddGeometryAttributes(tranzit_zone_polygon, "AREA", "", "SQUARE_METERS")
        area_tranzit_zone = [k[0] for k in arcpy.da.SearchCursor(tranzit_zone_polygon, "POLY_AREA")][0]

        arcpy.management.AddGeometryAttributes(runout_polygon, "AREA", "", "SQUARE_METERS")
        area_runout_zone = [k[0] for k in arcpy.da.SearchCursor(runout_polygon, "POLY_AREA")][0]

        arcpy.edit.Densify(tranzit_track, "DISTANCE", cell_p)
        arcpy.FeatureVerticesToPoints_management(tranzit_track, "tranzit_track_point_1", "ALL")
        arcpy.sa.ExtractValuesToPoints('tranzit_track_point_1', slope_degree, "tranzit_track_point_1_slope")
        slope_tranzit_zone = [k[0] for k in arcpy.da.SearchCursor('tranzit_track_point_1_slope', "RASTERVALU")]
        sum = 0
        for i in range(len(slope_tranzit_zone)):
            sum += slope_tranzit_zone[i]
        median_slope_tranzit = sum/len(slope_tranzit_zone)

        merge_list_start_tranz = [start_track, tranzit_track]
        arcpy.Merge_management(merge_list_start_tranz, "start_tranzit_line")
        arcpy.edit.Densify('start_tranzit_line', "DISTANCE", cell_p)
        arcpy.FeatureVerticesToPoints_management('start_tranzit_line', "split_line_tranz_start_point", "ALL")
        arcpy.sa.ExtractValuesToPoints('split_line_tranz_start_point', slope_degree, "split_line_tranz_start_point_slope")
        slope_tranzit_start_zone = [k[0] for k in arcpy.da.SearchCursor('split_line_tranz_start_point_slope', "RASTERVALU")]
        sum = 0
        for i in range(len(slope_tranzit_start_zone)):
            sum += slope_tranzit_start_zone[i]
        median_slope_tranzit_start = sum/len(slope_tranzit_start_zone)

        
        
        

#СОЗДАНИЕ ТЕКСТОВОГО ФАЙЛА СОДЕРЖАЩЕГО ОСНОВНЫЕ ПАРАМЕТРЫ ЛАВИНЫ
        with open(output_text, "w") as file:
            file.write('Initial data: \n Pixel size {0} m \n Snow height {1} mm \n\n'.format(cell_p, snow_height))

            file.write('Data received: \nStart point coordinates: X - {0}; Y - {1}; Z - {2}; \n'.format(coords_start_x,coords_start_y,z_start_point))
            file.write('Coordinates of the end point of the start zone: X - {0}; Y - {1}; Z - {2}; \n'.format(coords_25_x,coords_25_y,z_25_point))
            file.write('Coordinates of the end point of the tranzit zone: X - {0}; Y - {1}; Z - {2}; \n'.format(coords_20_x,coords_20_y,z_20_point))
            file.write('Coordinates of the end point of the runout zone: X - {0}; Y - {1}; Z - {2}; \n\n'.format(coords_end_x,coords_end_y,z_end_point))

            file.write('Start line length: {0} m \n'.format(len_start))
            file.write('Tranzit line length: {0} m \n'.format(len_tranzit))
            file.write('Runout line length: {0} m \n\n'.format(len_runout))

            file.write('Start zone area: {0} m^2 \n'.format(area_start_zone))
            file.write('Tranzit zone area: {0} m^2 \n'.format(area_tranzit_zone))
            file.write('Runouth zone area: {0} m^2 \n\n'.format(area_runout_zone))

            file.write('Average slope along the starting line: {0} ° \n'.format(median_slope))
            file.write('Average slope along the transit line: {0} ° \n'.format(median_slope_tranzit))
            file.write('Average slope along the start line and transit line: {0}° \n\n'.format(median_slope_tranzit_start))

            file.write('Speed at the end of the starting zone: {0} m/s \n'.format(v_25))
            file.write('Speed at the end of the tranzit zone: {0} m/s \n'.format(v_20))

            file.write('Total line length: {0} m \n'.format(L))
            file.write('Total elevation difference: {0} m \n'.format(H))


#  ЗАПИСЬ ИЗ ВРЕМЕННЫХ СЛОЕВ В ПОСТОЯННЫЕ
            path_dir_wsh = os.path.abspath(os.path.join(str(watershed_output), os.pardir))
            path_dir_tra = os.path.abspath(os.path.join(str(tranzit_zone_polygon), os.pardir))
            path_dir_ra = os.path.abspath(os.path.join(str(runout_polygon), os.pardir))
            path_dir_st = os.path.abspath(os.path.join(str(start_track), os.pardir))
            path_dir_tt = os.path.abspath(os.path.join(str(tranzit_track), os.pardir))
            path_dir_rt = os.path.abspath(os.path.join(str(runout_track), os.pardir))

            name_wsh_str = str(watershed_output)
            name_wsh_all =  name_wsh_str.split('\\')
            name_wsh = name_wsh_all[-1]

            name_tra_str = str(tranzit_zone_polygon)
            name_tra_all =  name_tra_str.split('\\')
            name_tra = str(name_tra_all[-1])

            name_ra_str = str(runout_polygon)
            name_ra_all =  name_ra_str.split('\\')
            name_ra = name_ra_all[-1]

            name_st_str = str(start_track)
            name_st_all =  name_st_str.split('\\')
            name_st = name_st_all[-1]

            name_tt_str = str(tranzit_track)
            name_tt_all =  name_tt_str.split('\\')
            name_tt = name_tt_all[-1]

            name_rt_str = str(runout_track)
            name_rt_all =  name_rt_str.split('\\')
            name_rt = name_rt_all[-1]


            arcpy.conversion.FeatureClassToFeatureClass(watershed_output, path_dir_wsh, name_wsh)
            arcpy.conversion.FeatureClassToFeatureClass(tranzit_zone_polygon, path_dir_tra,name_tra)
            arcpy.conversion.FeatureClassToFeatureClass(runout_polygon, path_dir_ra, name_ra)

            arcpy.conversion.FeatureClassToFeatureClass(start_track, path_dir_st, name_st)
            arcpy.conversion.FeatureClassToFeatureClass(tranzit_track, path_dir_tt, name_tt)
            arcpy.conversion.FeatureClassToFeatureClass(runout_track, path_dir_rt, name_rt)
            


            




            
            










#         # Добавить удаление всех промежуточных слоев, сохранение промежуточных водораздела и пути не во временные?. Добавить месседжы, исправить названия в окне ввода.
#         # благовещенский определение лавинных нагрузок 62-63
            